"""Raid planning for one barbarian: probe or raid, which troops, how many, and how much it pays per hour."""

from dataclasses import dataclass, field
from typing import Any

from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.knowledge import UNITS
from tribal_assistant.core.agents.target_intel import TargetIntel

WORLD_SPEED = 2.0
UNIT_SPEED = 0.5
RAIDERS = ("light", "knight", "spear", "axe", "marcher")
CAVALRY = ("light", "knight", "marcher")
INFANTRY = ("spear", "sword", "axe", "archer")
RADIUS = {"spear": "raid.radius_infantry", "sword": "raid.radius_infantry", "axe": "raid.radius_infantry", "archer": "raid.radius_infantry", "light": "raid.radius_cavalry", "marcher": "raid.radius_cavalry", "knight": "raid.radius_cavalry"}
WALL_LIGHT = {0: 1, 1: 2, 2: 8, 3: 22, 4: 46, 5: 85}


@dataclass
class RaidPlan:
    coords: str
    kind: str
    why: str
    squad: dict[str, int] = field(default_factory=dict)
    haul: float = 0.0
    rate: float = 0.0


class RaidPlanner:
    @staticmethod
    def minutes_per_field(unit: str) -> float:
        return UNITS[unit].speed / UNIT_SPEED

    @classmethod
    def trip_minutes(cls, squad: dict[str, int], distance: float) -> float:
        """One way: the slowest unit sets the pace."""
        return distance * max((cls.minutes_per_field(u) for u, n in squad.items() if n > 0 and u in UNITS), default=0.0)

    @staticmethod
    def in_range(unit: str, distance: float, knobs: Knobs | None = None) -> bool:
        return unit in RADIUS and distance <= (knobs or Knobs()).int(RADIUS[unit])

    @staticmethod
    def max_raids(light: int, per_hour: int, sent_last_hour: int, knobs: Knobs | None = None) -> int:
        knobs = knobs or Knobs()
        wanted = knobs.int("raid.max_base") + light // knobs.int("raid.light_per_raid")
        return max(0, min(wanted, knobs.int("raid.max_cap"), per_hour - sent_last_hour))

    @staticmethod
    def wall_light(wall: int | None, has_ram: bool = False, knobs: Knobs | None = None) -> int | None:
        """Light cavalry that clears a barbarian behind this wall without losses; None means leave it alone."""
        if wall is None:
            return 0

        knobs = knobs or Knobs()
        if wall >= knobs.int("raid.ram_wall") and not has_ram:
            return None

        base = WALL_LIGHT.get(wall)
        return None if base is None else max(1, round(base * knobs.get("raid.wall_light_factor")))

    @staticmethod
    def paladin_allowed(data: dict[str, Any], points: int, knobs: Knobs | None = None) -> bool:
        return data.get("last_result") == "green" or 0 < points <= (knobs or Knobs()).int("raid.paladin_points")

    @staticmethod
    def production(level: int) -> float:
        return (30 * 1.163118 ** (level - 1) if level > 0 else 5) * WORLD_SPEED

    @staticmethod
    def storage(level: int) -> float:
        return 1000 * 1.2294934 ** (max(level, 1) - 1)

    @staticmethod
    def hidden(level: int) -> float:
        return 150 * 1.3335 ** (level - 1) if level > 0 else 0.0

    @classmethod
    def haul_estimate(cls, scouted: dict[str, int], buildings: dict[str, int], hours: float) -> int:
        """Scouted stock plus what the mines make until the troops land, capped by the storage, minus the hiding place."""
        cap = cls.storage(buildings.get("storage", 1))
        hide = cls.hidden(buildings.get("hide", 0))
        total = 0.0
        for resource, building in (("wood", "wood"), ("clay", "stone"), ("iron", "iron")):
            amount = min(cap, scouted.get(resource, 0) + cls.production(buildings.get(building, 1)) * hours)
            total += max(0.0, amount - hide)

        return int(total)

    @classmethod
    def expected(cls, data: dict[str, Any], travel_hours: float) -> int | None:
        if not data.get("scouted") or not TargetIntel.fresh_scouting(data):
            return None

        hours = (TargetIntel.age_hours(data, "scouted_at") or 0.0) + travel_hours
        return cls.haul_estimate(data["scouted"], data.get("buildings") or {}, hours)

    @staticmethod
    def carry(squad: dict[str, int]) -> int:
        return sum(UNITS[u].carry * n for u, n in squad.items() if u in UNITS)

    @classmethod
    def squad(cls, home: dict[str, int], want: int, knobs: Knobs | None = None) -> dict[str, int] | None:
        """Smallest group of raiders, fastest carriers first, that can take `want` resources."""
        squad: dict[str, int] = {}
        carried = 0
        for unit in RAIDERS:
            capacity = UNITS[unit].carry if unit in UNITS else 0
            if not capacity or home.get(unit, 0) <= 0 or carried >= want:
                continue

            count = min(home[unit], -(-(want - carried) // capacity))
            squad[unit] = count
            carried += count * capacity

        if not squad or carried < min(want, (knobs or Knobs()).int("raid.unknown_haul")) * (knobs or Knobs()).get("raid.min_carry_share"):
            return None

        return squad

    @staticmethod
    def secure(squad: dict[str, int], home: dict[str, int], light_needed: int, knobs: Knobs | None = None) -> dict[str, int] | None:
        """Enough light cavalry for the wall, and never a handful of infantry on its own."""
        minimum = (knobs or Knobs()).int("raid.min_infantry")
        squad = dict(squad)

        if light_needed:
            if home.get("light", 0) < light_needed:
                return None

            squad["light"] = max(squad.get("light", 0), light_needed)

        infantry = sum(squad.get(u, 0) for u in INFANTRY)
        if infantry and infantry < minimum and not squad.get("knight"):
            spare = sum(home.get(u, 0) for u in INFANTRY) - infantry
            if infantry + spare >= minimum:
                need = minimum - infantry
                for unit in INFANTRY:
                    add = min(home.get(unit, 0) - squad.get(unit, 0), need)
                    if add > 0:
                        squad[unit] = squad.get(unit, 0) + add
                        need -= add
            elif any(squad.get(u) for u in CAVALRY):
                squad = {u: n for u, n in squad.items() if u not in INFANTRY}
            else:
                return None

        return {u: n for u, n in squad.items() if n > 0} or None

    @classmethod
    def needs_probe(cls, data: dict[str, Any], points: int, median: float) -> bool:
        if "scouted" not in data and not data.get("attacks"):
            return True

        if data.get("yellow_streak", 0) >= 1 and not TargetIntel.fresh_scouting(data):
            return True

        return points > median and "scouted" not in data

    @classmethod
    def plan(cls, target: dict[str, Any], data: dict[str, Any], home: dict[str, int], median: float, has_ram: bool = False, knobs: Knobs | None = None) -> RaidPlan:
        knobs = knobs or Knobs()
        coords = str(target["coords"])
        distance = float(target.get("distance") or 0)
        points = int(target.get("points") or 0)
        big = points > median and "scouted" not in data

        if target.get("recently_attacked"):
            return RaidPlan(coords, "skip", "atacado há pouco")

        if data.get("defenders_left", 0) > 0:
            return RaidPlan(coords, "skip", f"{data['defenders_left']} defensor(es) na aldeia segundo o último relatório")

        if cls.needs_probe(data, points, median):
            spies = knobs.int("spy.min_send")
            if home.get("spy", 0) >= spies and cls.in_range("light", distance, knobs):
                return RaidPlan(coords, "probe", "alvo grande sem espionagem" if big else "sondar antes de saquear", {"spy": spies})

            if big:
                return RaidPlan(coords, "skip", "bárbara grande sem espionagem e sem exploradores")

            if data.get("yellow_streak", 0) >= knobs.int("raid.yellow_streak_skip"):
                return RaidPlan(coords, "skip", f"{data['yellow_streak']} relatórios amarelos seguidos")

        wall = data.get("wall")
        light_needed = cls.wall_light(wall, has_ram, knobs)
        if light_needed is None:
            return RaidPlan(coords, "skip", f"muralha {wall}: precisa de aríetes")

        allowed = {u: n for u, n in home.items() if u in RAIDERS and n > 0 and cls.in_range(u, distance, knobs)}
        if wall:
            allowed = {u: n for u, n in allowed.items() if u in CAVALRY}

        if not cls.paladin_allowed(data, points, knobs):
            allowed.pop("knight", None)

        if not allowed:
            return RaidPlan(coords, "skip", f"nenhuma tropa alcança {distance:.1f} campos no raio seguro")

        pace = min(cls.minutes_per_field(u) for u in allowed)
        expected = cls.expected(data, distance * pace / 60)
        want = expected if expected is not None else int((data.get("avg_haul") or knobs.int("raid.unknown_haul")) * knobs.get("raid.history_margin"))
        if want <= 0:
            return RaidPlan(coords, "skip", "espionagem mostra aldeia vazia")

        squad = cls.squad(allowed, want, knobs)
        squad = cls.secure(squad, allowed, light_needed if wall else 0, knobs) if squad else None
        if squad is None:
            return RaidPlan(coords, "skip", "tropas insuficientes para um grupo seguro")

        escort = knobs.int("raid.escort_spies")
        if wall == 0 and home.get("spy", 0) >= escort:
            squad["spy"] = escort

        carry = cls.carry(squad)
        haul = min(float(want if expected is not None else data.get("avg_haul") or carry * knobs.get("raid.unknown_fill_share")), float(carry))
        hours = 2 * cls.trip_minutes(squad, distance) / 60
        why = f"espionado: ~{expected} recursos na chegada" if expected is not None else "histórico de relatórios"
        return RaidPlan(coords, "raid", why, squad, haul, haul / hours if hours else haul)
