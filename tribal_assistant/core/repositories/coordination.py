"""Data access for village roles and coordinator rounds."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.models.coordination import CoordinationRound, VillageStrategy


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CoordinationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def strategy(self, village_id: int) -> VillageStrategy | None:
        return await self.session.get(VillageStrategy, village_id)

    async def set_strategy(self, village_id: int, role: str, reason: str, manual: bool) -> VillageStrategy:
        row = await self.strategy(village_id)
        if row is None:
            row = VillageStrategy(village_id=village_id, role=role, updated_at=_now())
            self.session.add(row)

        row.role, row.reason, row.manual, row.updated_at = role, reason[:255], manual, _now()
        await self.session.commit()
        return row

    async def save_round(
        self, run_id: str, village_id: int, role: str, mode: str, goal: str, next_review_at: datetime | None, data: dict[str, Any]
    ) -> None:
        self.session.add(
            CoordinationRound(
                run_id=run_id,
                village_id=village_id,
                created_at=_now(),
                role=role,
                mode=mode,
                goal=goal,
                next_review_at=next_review_at,
                data=json.dumps(data, ensure_ascii=False, default=str),
            )
        )
        await self.session.commit()

    async def latest(self) -> Sequence[CoordinationRound]:
        rows = (await self.session.execute(select(CoordinationRound).order_by(CoordinationRound.id.desc()).limit(50))).scalars().all()
        seen: dict[int, CoordinationRound] = {}
        for row in rows:
            seen.setdefault(row.village_id, row)

        return list(seen.values())

    async def history(self, village_id: int, limit: int = 20) -> Sequence[CoordinationRound]:
        stmt = (
            select(CoordinationRound)
            .where(CoordinationRound.village_id == village_id)
            .order_by(CoordinationRound.id.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def prune(self, days: int) -> int:
        result = await self.session.execute(delete(CoordinationRound).where(CoordinationRound.created_at < _now() - timedelta(days=days)))
        await self.session.commit()
        return result.rowcount or 0
