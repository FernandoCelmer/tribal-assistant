"""How far each building may run ahead: main building, pits and the military buildings."""

from tribal_assistant.core.agents.knobs import Knobs

PIT_MAX = 30


class BuildPacing:
    @staticmethod
    def main_cap(levels: dict[str, int], knobs: Knobs | None = None) -> int:
        knobs = knobs or Knobs()
        return knobs.int("pacing.main_early_cap") if levels.get("stable", 0) < knobs.int("pacing.stable_gate") else knobs.int("pacing.main_late_cap")

    @staticmethod
    def military_due(levels: dict[str, int], protected: bool, knobs: Knobs | None = None) -> list[str]:
        """After protection, every few main levels past the early cap call for more barracks and stable levels."""
        knobs = knobs or Knobs()
        gate = knobs.int("pacing.stable_gate")
        if protected or levels.get("stable", 0) < gate:
            return []

        steps = max(0, levels.get("main", 0) - knobs.int("pacing.main_early_cap")) // knobs.int("pacing.military_every")
        per_step = knobs.int("pacing.military_step")
        wanted = {"barracks": knobs.int("pacing.barracks_base") + per_step * steps, "stable": gate + per_step * steps}
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
