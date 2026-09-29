"""When the first noble is worth chasing, and which barbarian it should take."""

from dataclasses import dataclass

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.game.world_config import FARM_BONUS

ACADEMY_PATH = (("main", 20), ("smith", 20), ("market", 10))
MIN_FARM = 24
MIN_ARMY_POP = 2000


@dataclass(frozen=True)
class Candidate:
    coords: str
    points: int
    distance: float
    bonus_id: int = 0
    known: bool = False


class NobleReadiness:
    @staticmethod
    def path_progress(levels: dict[str, int]) -> float:
        return sum(min(1.0, levels.get(b, 0) / lvl) for b, lvl in ACADEMY_PATH) / len(ACADEMY_PATH)

    @staticmethod
    def army_pop(ctx: VillageContext) -> int:
        return sum(u.total * (u.cost_pop or 1) for u in ctx.village.units if u.name not in ("snob", "knight", "militia"))

    @classmethod
    def missing(cls, ctx: VillageContext) -> list[str]:
        levels = ctx.levels
        gaps = [f"{b} {lvl}" for b, lvl in ACADEMY_PATH if levels.get(b, 0) < lvl]
        if levels.get("farm", 0) < MIN_FARM:
            gaps.append(f"farm {MIN_FARM}")
        if cls.army_pop(ctx) < MIN_ARMY_POP:
            gaps.append(f"exército {MIN_ARMY_POP} pop")
        return gaps

    @classmethod
    def ready(cls, ctx: VillageContext) -> bool:
        return not cls.missing(ctx)


class NobleTarget:
    """Prefer a nearby barbarian already scouted or farmed (farm bonus first); else the biggest nearby barbarian."""

    @staticmethod
    def pick(candidates: list[Candidate], max_distance: float = 10.0) -> Candidate | None:
        near = [c for c in candidates if c.distance <= max_distance]
        known = [c for c in near if c.known]
        if known:
            return min(known, key=lambda c: (c.bonus_id != FARM_BONUS, c.distance, -c.points))

        if near:
            return max(near, key=lambda c: (c.bonus_id == FARM_BONUS, c.points, -c.distance))

        return None
