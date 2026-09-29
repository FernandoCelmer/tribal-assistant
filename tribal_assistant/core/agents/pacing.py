"""How far each building may run ahead: main building, pits and the military buildings."""

MAIN_EARLY_CAP = 10
STABLE_GATE = 3
IRON_GAP = 3


class BuildPacing:
    @staticmethod
    def main_cap(levels: dict[str, int]) -> int:
        return MAIN_EARLY_CAP if levels.get("stable", 0) < STABLE_GATE else 20

    @staticmethod
    def military_due(levels: dict[str, int], protected: bool) -> list[str]:
        """After protection, every 3 main levels past 10 call for 2 barracks and 2 stable levels."""
        if protected or levels.get("stable", 0) < STABLE_GATE:
            return []

        steps = max(0, levels.get("main", 0) - MAIN_EARLY_CAP) // 3
        wanted = {"barracks": 5 + 2 * steps, "stable": STABLE_GATE + 2 * steps}
        return [b for b, target in wanted.items() if levels.get(b, 0) < target]

    @staticmethod
    def pit_caps(levels: dict[str, int]) -> dict[str, int]:
        """Wood stays the highest pit; iron trails wood and clay by 3 until the stable exists."""
        wood, clay = levels.get("wood", 0), levels.get("stone", 0)
        iron_cap = wood if levels.get("stable", 0) >= 1 else max(1, min(wood, clay) - IRON_GAP)
        return {"wood": 30, "stone": min(30, max(wood, 1)), "iron": min(30, iron_cap)}

    @classmethod
    def pits(cls, levels: dict[str, int]) -> list[str]:
        """Pits allowed to grow one more level now, lowest first, wood winning ties."""
        caps = cls.pit_caps(levels)
        order = ("wood", "stone", "iron")
        allowed = [p for p in order if levels.get(p, 0) + 1 <= caps[p]]
        return sorted(allowed, key=lambda p: (levels.get(p, 0), order.index(p)))
