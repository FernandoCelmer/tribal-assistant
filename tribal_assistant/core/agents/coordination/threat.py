"""Nearby players that could hurt a village, from the public world files."""

import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.models.world import WorldPlayer, WorldVillage


@dataclass(frozen=True)
class Threat:
    player: str
    points: int
    distance: float


class ThreatScan:
    RADIUS = 8

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def near(self, ctx: VillageContext, radius: int | None = None) -> list[Threat]:
        radius = radius or self.RADIUS
        x, y = (int(n) for n in ctx.village.coords.split("|"))
        own_player = (ctx.player or {}).get("id")
        own_name, own_ally = await self.own(ctx)
        rows = (
            await self.session.execute(
                select(WorldVillage, WorldPlayer)
                .join(WorldPlayer, WorldPlayer.id == WorldVillage.player_id)
                .where(WorldVillage.player_id > 0)
                .where(WorldVillage.x.between(x - radius, x + radius))
                .where(WorldVillage.y.between(y - radius, y + radius))
            )
        ).all()

        threats: dict[str, Threat] = {}
        for village, player in rows:
            if (village.x, village.y) == (x, y) or (own_player and str(player.id) == str(own_player)):
                continue

            if player.name == own_name or (own_ally and player.ally_id == own_ally):
                continue

            distance = round(math.hypot(village.x - x, village.y - y), 1)
            current = threats.get(player.name)
            if current is None or distance < current.distance:
                threats[player.name] = Threat(player.name, player.points, distance)

        return sorted(threats.values(), key=lambda t: t.distance)

    async def own(self, ctx: VillageContext) -> tuple[str | None, int | None]:
        """Own player name and tribe id: from the synced player, else from the world player list."""
        player = ctx.player or {}
        name = player.get("name") or None
        ally = player.get("ally_id") or player.get("ally")
        if ally and str(ally) != "0":
            return name, int(ally)

        if not name:
            return None, None

        row = (await self.session.execute(select(WorldPlayer).where(WorldPlayer.name == name))).scalars().first()
        return name, (row.ally_id or None) if row else None

    @staticmethod
    def dangerous(threats: list[Threat], own_points: int, within: float = 5.0) -> list[Threat]:
        return [t for t in threats if t.distance <= within and t.points >= max(300, own_points * 2)]
