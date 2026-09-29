"""World data repository — bulk replace and spatial lookups."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.client.world import WorldData
from tribal_assistant.models.world import WorldAlly, WorldPlayer, WorldSetting, WorldVillage

_CHUNK = 4000


class WorldRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace(self, data: WorldData) -> None:
        for model, rows in (
            (WorldVillage, data.villages),
            (WorldPlayer, data.players),
            (WorldAlly, data.allies),
        ):
            await self.session.execute(delete(model))
            for start in range(0, len(rows), _CHUNK):
                await self.session.execute(insert(model), rows[start : start + _CHUNK])
        now = datetime.now(UTC).replace(tzinfo=None)
        for key, value in data.settings.items():
            await self.session.merge(WorldSetting(key=key, data=json.dumps(value), fetched_at=now))
        await self.session.commit()

    async def setting(self, key: str) -> dict[str, Any]:
        row = await self.session.get(WorldSetting, key)
        return json.loads(row.data) if row else {}

    async def fetched_at(self) -> datetime | None:
        result = await self.session.execute(select(func.max(WorldSetting.fetched_at)))
        return result.scalar_one_or_none()

    async def counts(self) -> dict[str, int]:
        counts = {}
        for name, model in (
            ("villages", WorldVillage),
            ("players", WorldPlayer),
            ("allies", WorldAlly),
        ):
            counts[name] = (await self.session.execute(select(func.count()).select_from(model))).scalar_one()
        return counts

    async def villages_in_box(
        self, x: int, y: int, radius: int, player_id: int | None
    ) -> Sequence[tuple[WorldVillage, WorldPlayer | None, WorldAlly | None]]:
        stmt = (
            select(WorldVillage, WorldPlayer, WorldAlly)
            .outerjoin(WorldPlayer, WorldPlayer.id == WorldVillage.player_id)
            .outerjoin(WorldAlly, WorldAlly.id == WorldPlayer.ally_id)
            .where(
                WorldVillage.x.between(x - radius, x + radius),
                WorldVillage.y.between(y - radius, y + radius),
            )
        )
        if player_id is not None:
            stmt = stmt.where(WorldVillage.player_id == player_id)
        result = await self.session.execute(stmt)
        return [tuple(row) for row in result.all()]
