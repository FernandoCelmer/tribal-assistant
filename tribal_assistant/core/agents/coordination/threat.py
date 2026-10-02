"""Nearby players that could hurt a village, from the public world files: points, fights and conquests."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.sightings import SightingBook
from tribal_assistant.core.models.world import WorldCombat, WorldConquest, WorldPlayer, WorldVillage


@dataclass(frozen=True)
class Threat:
    player: str
    points: int
    distance: float
    player_id: str = ""
    attack: int = 0
    attacking: bool = False
    conquests: int = 0

    def describe(self) -> str:
        parts = [f"{self.player} a {self.distance} campos, {self.points} pts"]
        if self.attack:
            parts.append(f"derrotou {self.attack} atacando" + (" (atacou desde o último sync)" if self.attacking else ""))
        if self.conquests:
            parts.append(f"{self.conquests} conquista(s) recente(s)")
        return ", ".join(parts)


class ThreatScan:
    def __init__(self, session: AsyncSession, knobs: Knobs | None = None) -> None:
        self.session = session
        self.knobs = knobs or Knobs()
        self.expanding: set[str] = set()

    async def near(self, ctx: VillageContext, radius: int | None = None) -> list[Threat]:
        radius = radius or self.knobs.int("threat.radius")
        x, y = (int(n) for n in ctx.village.coords.split("|"))
        own_player = (ctx.player or {}).get("id")
        own_name, own_ally = await self.own(ctx)
        self.expanding = await SightingBook(self.session).expanding(self.knobs.get("threat.expanding_hours"))
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
                threats[player.name] = Threat(player.name, player.points, distance, str(player.id))

        return await self._fights(sorted(threats.values(), key=lambda t: t.distance))

    async def _fights(self, threats: list[Threat]) -> list[Threat]:
        """Fight scores and recent conquests of each nearby player; attackers and conquerors count as expanding."""
        ids = [int(t.player_id) for t in threats if t.player_id.isdigit()]
        if not ids:
            return threats

        now = datetime.now(UTC).replace(tzinfo=None)
        active = now - timedelta(hours=self.knobs.get("threat.active_hours"))
        combat = {r.id: r for r in (await self.session.execute(select(WorldCombat).where(WorldCombat.id.in_(ids)))).scalars().all()}
        recent = (
            await self.session.execute(
                select(WorldConquest.new_owner).where(WorldConquest.new_owner.in_(ids), WorldConquest.at >= now - timedelta(hours=self.knobs.get("threat.expanding_hours")))
            )
        ).scalars().all()

        result = []
        for threat in threats:
            pid = int(threat.player_id) if threat.player_id.isdigit() else 0
            row = combat.get(pid)
            attacking = bool(row and row.attack_gain > 0 and row.attacked_at and row.attacked_at >= active)
            conquests = sum(1 for owner in recent if owner == pid)
            if attacking or conquests:
                self.expanding.add(threat.player_id)
            result.append(Threat(threat.player, threat.points, threat.distance, threat.player_id, row.attack if row else 0, attacking, conquests))
        return result

    @staticmethod
    def summary(threats: list[Threat], limit: int = 4) -> str:
        rows = [t.describe() for t in threats[:limit]]
        return "Vizinhos: " + " · ".join(rows) if rows else ""

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

    def dangerous(self, threats: list[Threat], own_points: int, within: float | None = None) -> list[Threat]:
        within = within if within is not None else self.knobs.get("threat.danger_distance")
        floor = max(self.knobs.int("threat.danger_points"), own_points * self.knobs.get("threat.danger_ratio"))
        return [t for t in threats if t.distance <= within and (t.points >= floor or t.player_id in self.expanding)]
