"""How far each building may run ahead: main building, pits and the military buildings."""

from tribal_assistant.core.agents.knobs import Knobs

STABLE_GATE = 3
MAIN_LATE_CAP = 20
PIT_MAX = 30


class BuildPacing:
    @staticmethod
    def main_cap(levels: dict[str, int], knobs: Knobs | None = None) -> int:
        early = (knobs or Knobs()).int("pacing.main_early_cap")
        return early if levels.get("stable", 0) < STABLE_GATE else MAIN_LATE_CAP

    @staticmethod
    def military_due(levels: dict[str, int], protected: bool, knobs: Knobs | None = None) -> list[str]:
        """After protection, every 3 main levels past the early cap call for 2 barracks and 2 stable levels."""
        if protected or levels.get("stable", 0) < STABLE_GATE:
            return []

        steps = max(0, levels.get("main", 0) - (knobs or Knobs()).int("pacing.main_early_cap")) // 3
        wanted = {"barracks": 5 + 2 * steps, "stable": STABLE_GATE + 2 * steps}
        return [b for b, target in wanted.items() if levels.get(b, 0) < target]

    @staticmethod
    def pit_caps(levels: dict[str, int], knobs: Knobs | None = None) -> dict[str, int]:
        """Wood stays the highest pit; iron trails wood and clay by the iron gap until the stable exists."""
        wood, clay = levels.get("wood", 0), levels.get("stone", 0)
        gap = (knobs or Knobs()).int("pacing.iron_gap")
        iron_cap = wood if levels.get("stable", 0) >= 1 else max(1, min(wood, clay) - gap)
        return {"wood": PIT_MAX, "stone": min(PIT_MAX, max(wood, 1)), "iron": min(PIT_MAX, iron_cap)}

    @classmethod
    def pits(cls, levels: dict[str, int], knobs: Knobs | None = None) -> list[str]:
        """Pits allowed to grow one more level now, lowest first, wood winning ties."""
        caps = cls.pit_caps(levels, knobs)
        order = ("wood", "stone", "iron")
        allowed = [p for p in order if levels.get(p, 0) + 1 <= caps[p]]
        return sorted(allowed, key=lambda p: (levels.get(p, 0), order.index(p)))
