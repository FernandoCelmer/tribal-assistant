"""World service — status and neighbourhood search over the public world data."""

import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.core.game.world_config import WorldConfig
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.repositories.world import WorldRepository
from tribal_assistant.core.schemas.world import NearbyVillage, WorldStatus

TRAVEL_UNITS = ("spear", "axe", "spy", "light", "heavy", "ram", "snob")


class WorldService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = WorldRepository(session)

    async def status(self) -> WorldStatus:
        config = await self.repository.setting("config")
        counts = await self.repository.counts()
        return WorldStatus(
            fetched_at=await self.repository.fetched_at(),
            speed=config.get("speed"),
            unit_speed=config.get("unit_speed"),
            **counts,
        )

    async def config(self) -> WorldConfig:
        return WorldConfig.from_settings(await self.repository.setting("config"), await self.repository.setting("units"))

    async def _origin(self, village_id: int | None) -> Village:
        stmt = select(Village).where(Village.is_own.is_(True))
        if village_id is not None:
            stmt = stmt.where(Village.id == village_id)
        village = (await self.session.execute(stmt.order_by(Village.id))).scalars().first()
        if village is None:
            raise NotFoundError("nenhuma aldeia própria sincronizada")
        return village

    async def nearby(
        self, village_id: int | None, kind: str, radius: int, limit: int
    ) -> list[NearbyVillage]:
        origin = await self._origin(village_id)
        ox, oy = (int(n) for n in origin.coords.split("|"))
        units = await self.repository.setting("units")

        rows = await self.repository.villages_in_box(
            ox, oy, radius, 0 if kind == "barbarian" else None
        )
        result = []
        for village, player, ally in rows:
            coords = f"{village.x}|{village.y}"
            if coords == origin.coords or (kind == "player" and village.player_id == 0):
                continue
            distance = math.hypot(village.x - ox, village.y - oy)
            if distance > radius:
                continue
            result.append(
                NearbyVillage(
                    id=village.id,
                    name=village.name,
                    coords=coords,
                    points=village.points,
                    distance=round(distance, 2),
                    player_id=village.player_id,
                    player_name=player.name if player else None,
                    ally_tag=ally.tag if ally else None,
                    is_barbarian=village.player_id == 0,
                    travel_minutes={
                        unit: round(distance * float(units[unit]["speed"]), 1)
                        for unit in TRAVEL_UNITS
                        if isinstance(units.get(unit), dict) and units[unit].get("speed")
                    },
                )
            )
        result.sort(key=lambda v: v.distance)
        return result[:limit]
