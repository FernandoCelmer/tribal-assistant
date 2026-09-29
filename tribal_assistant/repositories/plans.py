"""Village plans: one row per village, steps stored as JSON."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.models.agent import VillagePlan
from tribal_assistant.schemas.plan import PlanStep


class PlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, village_id: int) -> VillagePlan | None:
        stmt = select(VillagePlan).where(VillagePlan.village_id == village_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def all(self) -> Sequence[VillagePlan]:
        return (await self.session.execute(select(VillagePlan).order_by(VillagePlan.village_id))).scalars().all()

    async def save(
        self,
        village_id: int,
        steps: list[PlanStep],
        *,
        summary: str | None = None,
        source: str | None = None,
        refreshed: bool = False,
    ) -> VillagePlan:
        row = await self.get(village_id)
        now = datetime.now(UTC).replace(tzinfo=None)

        if row is None:
            row = VillagePlan(village_id=village_id, refreshed_at=now)
            self.session.add(row)

        row.steps = json.dumps([s.model_dump() for s in steps], ensure_ascii=False)
        if summary is not None:
            row.summary = summary
        if source is not None:
            row.source = source
        if refreshed:
            row.refreshed_at = now

        await self.session.commit()
        return row

    @staticmethod
    def steps(row: VillagePlan | None) -> list[PlanStep]:
        if row is None:
            return []
        return [PlanStep.model_validate(s) for s in json.loads(row.steps or "[]")]
