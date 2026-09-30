"""Farm assistant planning: the templates A and B a village should keep, and which one fits each barbarian."""

from dataclasses import dataclass, field
from typing import Any

from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.knowledge import UNITS
from tribal_assistant.core.agents.proposers.raid import RaidPlanner

SMALL_RAIDERS = ("light", "spear", "axe")


@dataclass
class FarmChoice:
    template: str
    why: str
    squad: dict[str, int] = field(default_factory=dict)
    target_id: int = 0


class FarmPlanner:
    @staticmethod
    def count(unit: str, carry: int) -> int:
        return -(-carry // UNITS[unit].carry)

    @classmethod
    def small(cls, totals: dict[str, int], knobs: Knobs) -> dict[str, int]:
        """Template A: the fastest raider the village has enough of to carry the A load."""
        carry = knobs.int("farm.template_a_carry")
        for unit in SMALL_RAIDERS:
            need = cls.count(unit, carry)
            if unit != "light":
                need = max(need, knobs.int("raid.min_infantry"))
            if totals.get(unit, 0) >= need:
                return {unit: need}
        return {}

    @classmethod
    def large(cls, totals: dict[str, int], walls: list[int], knobs: Knobs, small: dict[str, int]) -> dict[str, int]:
        """Template B: light cavalry for the B load, never less than the wall table asks for the walls in the list."""
        by_wall = [RaidPlanner.wall_light(w, False, knobs) or 0 for w in walls if 0 < w < knobs.int("raid.ram_wall")]
        need = max([cls.count("light", knobs.int("farm.template_b_carry")), *by_wall])
        if totals.get("light", 0) < need or need <= small.get("light", 0):
            return {}
        return {"light": need}

    @classmethod
    def templates(cls, totals: dict[str, int], walls: list[int], knobs: Knobs) -> dict[str, dict[str, int]]:
        a = cls.small(totals, knobs)
        return {"a": a, "b": cls.large(totals, walls, knobs, a)}

    @staticmethod
    def drifted(current: dict[str, dict[str, int]], wanted: dict[str, dict[str, int]], knobs: Knobs) -> bool:
        """True when a saved template is missing a unit, has another one, or is off by more than the tolerance."""
        tolerance = knobs.get("farm.template_tolerance")
        for letter, units in wanted.items():
            saved = current.get(letter) or {}
            if set(saved) != set(units):
                return True
            if any(abs(saved[u] - n) > tolerance * n for u, n in units.items()):
                return True
        return False

    @staticmethod
    def fits(squad: dict[str, int], home: dict[str, int], distance: float, knobs: Knobs) -> bool:
        return bool(squad) and all(home.get(u, 0) >= n and RaidPlanner.in_range(u, distance, knobs) for u, n in squad.items())

    @classmethod
    def choose(cls, row: dict[str, Any], data: dict[str, Any], templates: dict[str, dict[str, int]], home: dict[str, int], knobs: Knobs) -> FarmChoice | None:
        """A for open barbarians with a normal haul, B for recurring full hauls or a wall of 1-2; None keeps the rally point."""
        distance = float(row.get("distance") or 0)
        buttons = row.get("buttons") or {}
        wall = data.get("wall") if data.get("wall") is not None else row.get("wall")
        a, b = templates.get("a") or {}, templates.get("b") or {}
        b_ready = buttons.get("b") and cls.fits(b, home, distance, knobs)

        if wall:
            needed = RaidPlanner.wall_light(int(wall), False, knobs)
            if needed is None or not b_ready or b.get("light", 0) < needed:
                return None
            return FarmChoice("b", f"muralha {wall}: modelo B com {b.get('light', 0)} CL (tabela pede {needed})", b)

        streak = int(data.get("full_streak") or 0)
        if streak >= knobs.int("farm.full_streak_b") and b_ready:
            return FarmChoice("b", f"{streak} saques cheios seguidos: modelo B", b)

        if buttons.get("a") and cls.fits(a, home, distance, knobs):
            return FarmChoice("a", "muralha 0 e saque normal: modelo A", a)

        return None

    @staticmethod
    def hauls(targets: list[dict[str, Any]]) -> tuple[int, int]:
        seen = [row for row in targets if row.get("full") is not None]
        return sum(1 for row in seen if row["full"]), len(seen)
