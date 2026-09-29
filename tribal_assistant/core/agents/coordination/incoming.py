"""Incoming attacks read from the synced commands: origin, likely slowest unit, size guess and the dodge decision."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.threat import ThreatScan
from tribal_assistant.core.agents.knobs import Knobs, tuning
from tribal_assistant.core.agents.knowledge import UNITS
from tribal_assistant.core.game.battle import BattleResult, simulate_battle
from tribal_assistant.core.game.incoming import (
    IncomingLabel,
    TravelClock,
    distance,
    guess_army,
    tag_for,
)
from tribal_assistant.core.models.world import WorldPlayer, WorldVillage
from tribal_assistant.core.repositories.lessons import LessonRepository
from tribal_assistant.core.repositories.world import WorldRepository

HOSTILE = ("attack", "noble")


def _utc(value: Any) -> datetime:
    at = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return at if at.tzinfo else at.replace(tzinfo=UTC)


@dataclass
class IncomingAttack:
    kind: str
    arrival_at: datetime
    minutes_left: float
    origin: str | None
    player: str | None
    player_points: int | None
    origin_points: int | None
    same_tribe: bool
    distance: float | None
    size: str | None
    watchtower: bool
    first_seen: datetime
    unit: str | None
    tag: str
    sent_at: datetime | None
    army: dict[str, int] = field(default_factory=dict)

    @property
    def noble(self) -> bool:
        return self.kind == "noble" or self.unit == "snob"

    def to_dict(self) -> dict[str, Any]:
        return {
            "arrival_at": self.arrival_at.isoformat(timespec="seconds"),
            "minutes_left": round(self.minutes_left, 1),
            "origin": self.origin,
            "player": self.player,
            "player_points": self.player_points,
            "same_tribe": self.same_tribe,
            "distance": round(self.distance, 2) if self.distance is not None else None,
            "size": self.size,
            "watchtower": self.watchtower,
            "slowest_unit": self.unit,
            "tag": self.tag,
            "sent_at": self.sent_at.isoformat(timespec="seconds") if self.sent_at else None,
            "army_guess": self.army,
        }


@dataclass
class Assessment:
    attack: IncomingAttack
    action: str
    reason: str
    battle: BattleResult | None = None
    target: str | None = None
    troops: dict[str, int] = field(default_factory=dict)
    travel_minutes: float | None = None


class IncomingWatch:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.world = WorldRepository(session)
        self.lessons = LessonRepository(session)

    async def clock(self) -> TravelClock:
        return TravelClock.for_world(await self.world.setting("units"), await self.world.setting("config"))

    async def attacks(self, ctx: VillageContext, now: datetime | None = None) -> list[IncomingAttack]:
        now = now or datetime.now(UTC)
        clock = await self.clock()
        own_ally = await self._own_ally(ctx)
        found = []
        for command in ctx.commands:
            if command.get("direction") != "in" or command.get("kind") not in HOSTILE:
                continue

            found.append(await self._attack(ctx, command, clock, own_ally, now))

        return sorted(found, key=lambda a: a.arrival_at)

    async def _attack(self, ctx: VillageContext, command: dict[str, Any], clock: TravelClock, own_ally: int | None, now: datetime) -> IncomingAttack:
        parsed = IncomingLabel.parse(str(command.get("label") or ""))
        origin = parsed["origin"] or command.get("coords")
        arrival = _utc(command.get("arrival_at") or command.get("arrives_at"))
        first_seen = await self._first_seen(ctx, origin, arrival, now)
        fields = distance(origin, ctx.village.coords)
        unit = clock.slowest(fields, (arrival - first_seen).total_seconds() / 60)
        noble = command.get("kind") == "noble"
        village, player = await self._origin(origin)
        cap = (village.points if village else None) or (player.points if player else None)
        guess = guess_army("snob" if noble and unit is None else unit, parsed["size"], cap)
        sent = arrival.timestamp() - clock.minutes(unit, fields) * 60 if unit and fields else None

        return IncomingAttack(
            kind=str(command.get("kind")),
            arrival_at=arrival,
            minutes_left=max(0.0, (arrival - now).total_seconds() / 60),
            origin=origin,
            player=parsed["player"] or (player.name if player else None),
            player_points=player.points if player else None,
            origin_points=village.points if village else None,
            same_tribe=bool(own_ally and player and player.ally_id == own_ally),
            distance=fields,
            size=parsed["size"],
            watchtower=parsed["watchtower"],
            first_seen=first_seen,
            unit=unit,
            tag=tag_for(unit, parsed["size"], noble),
            sent_at=datetime.fromtimestamp(sent, UTC) if sent else None,
            army=guess.units if guess else {},
        )

    async def _first_seen(self, ctx: VillageContext, origin: str | None, arrival: datetime, now: datetime) -> datetime:
        key = f"incoming:{ctx.id}:{origin or '?'}:{arrival.strftime('%Y%m%d%H%M%S')}"
        row = await self.lessons.get(key)
        if row is None:
            row = await self.lessons.observe(key, "incoming", f"ataque de {origin or '?'} chega {arrival:%d/%m %H:%M:%S}", data={"first_seen": now.isoformat()})

        stamp = json.loads(row.data or "{}").get("first_seen")
        return min(_utc(stamp) if stamp else now, now)

    async def _origin(self, coords: str | None) -> tuple[WorldVillage | None, WorldPlayer | None]:
        if not coords or "|" not in coords:
            return None, None

        x, y = (int(n) for n in coords.split("|"))
        village = (await self.session.execute(select(WorldVillage).where(WorldVillage.x == x, WorldVillage.y == y))).scalars().first()
        if village is None or not village.player_id:
            return village, None

        player = (await self.session.execute(select(WorldPlayer).where(WorldPlayer.id == village.player_id))).scalars().first()
        return village, player

    async def _own_ally(self, ctx: VillageContext) -> int | None:
        return (await ThreatScan(self.session).own(ctx))[1]


class DodgePlanner:
    """Hold when the defense wins, the attack brings a noble or is only spies; dodge when it clearly overruns us."""

    def __init__(self, session: AsyncSession, clock: TravelClock, knobs: Knobs | None = None) -> None:
        self.session = session
        self.clock = clock
        self.knobs = knobs

    @staticmethod
    def home_army(ctx: VillageContext) -> dict[str, int]:
        return {u.name: u.home for u in ctx.village.units if u.home > 0 and u.name in UNITS}

    def decide(self, ctx: VillageContext, attack: IncomingAttack) -> Assessment:
        if attack.same_tribe:
            return Assessment(attack, "ignore", "comando de membro da própria tribo")

        if attack.noble:
            return Assessment(attack, "hold", "traz nobre: segurar a aldeia com tudo em casa")

        if attack.unit == "spy":
            return Assessment(attack, "hold", "só espiões: espiões em casa matam espiões")

        if not attack.army:
            return Assessment(attack, "hold", "tamanho desconhecido: segurar e reforçar")

        knobs = self.knobs or tuning(ctx)
        home = self.home_army(ctx)
        wall = ctx.levels.get("wall", 0)
        battle = simulate_battle(attack.army, home, wall)
        pop = sum(UNITS[u].pop * n for u, n in home.items())
        if battle.attacker_wins and battle.attacker_loss_ratio <= knobs.get("dodge.max_losses") and pop >= knobs.int("dodge.min_pop"):
            return Assessment(attack, "dodge", f"ataque estimado supera a defesa (perda deles {battle.attacker_loss_ratio:.0%})", battle, troops=home)

        why = "defesa segura o ataque estimado" if not battle.attacker_wins else "ataque pequeno demais para valer a esquiva"
        return Assessment(attack, "hold", why, battle)

    def slowest_home(self, troops: dict[str, int]) -> str | None:
        units = [u for u, n in troops.items() if n > 0]
        return max(units, key=lambda u: self.clock.table.get(u, 0)) if units else None

    def target(self, ctx: VillageContext, attack: IncomingAttack, troops: dict[str, int], barbarians: list[tuple[str, float]]) -> tuple[str, float] | None:
        """Closest barbarian far enough that the troops are still out when the attack lands."""
        slowest = self.slowest_home(troops)
        if slowest is None:
            return None

        knobs = self.knobs or tuning(ctx)
        radius, margin = knobs.int("dodge.radius"), knobs.int("dodge.margin_minutes")
        options = []
        for coords, fields in barbarians:
            if fields > radius:
                continue

            travel = self.clock.minutes(slowest, fields)
            if 2 * travel >= attack.minutes_left + margin and travel < attack.minutes_left + 24 * 60:
                options.append((travel, coords))

        if not options:
            return None

        travel, coords = min(options)
        return coords, travel
