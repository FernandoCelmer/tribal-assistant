from datetime import UTC, datetime
from typing import Any

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.schemas.game import BuildingOut, ScavengeOut, UnitOut, VillageOverview


def building(name: str, level: int, *, cost: int = 100, pop: int = 1, can_build: bool = True, **extra: Any) -> BuildingOut:
    return BuildingOut(
        name=name,
        label=name,
        level=level,
        max_level=30,
        next_level=level + 1,
        next_wood=cost,
        next_clay=cost,
        next_iron=cost,
        next_pop=pop,
        build_time=60,
        can_build=can_build,
        blocker=None,
        queued_level=extra.get("queued_level"),
        queued_until=None,
    )


def unit(name: str, home: int = 0, *, available: bool = True, cost: tuple[int, int, int, int] = (50, 30, 10, 1)) -> UnitOut:
    return UnitOut(
        name=name,
        home=home,
        total=home,
        away=0,
        available=available,
        max_recruit=999,
        cost_wood=cost[0],
        cost_clay=cost[1],
        cost_iron=cost[2],
        cost_pop=cost[3],
        build_time=30,
        blocker=None,
    )


def scavenge(option_id: int, *, locked: bool = False, unlocking: bool = False, busy: bool = False) -> ScavengeOut:
    now = datetime.now(UTC)
    return ScavengeOut(
        option_id=option_id,
        name=f"Coleta {option_id}",
        loot_factor=0.1 * option_id,
        is_locked=locked,
        unlock_at=now if unlocking else None,
        return_at=now if busy else None,
    )


def context(
    *,
    buildings: list[BuildingOut] | None = None,
    units: list[UnitOut] | None = None,
    stock: int = 1000,
    storage: int = 2000,
    pop_free: int = 100,
    quests: list[dict[str, Any]] | None = None,
    rewards: int = 0,
    scavenge_options: list[ScavengeOut] | None = None,
) -> VillageContext:
    village = VillageOverview(
        id=1,
        game_id="105765",
        name="Aldeia",
        coords="500|500",
        points=100,
        wood=stock,
        clay=stock,
        iron=stock,
        storage=storage,
        pop_current=100,
        pop_max=100 + pop_free,
        wood_prod=0,
        clay_prod=0,
        iron_prod=0,
        synced_at=datetime.now(UTC),
        buildings=buildings or [building("main", 3), building("wood", 4), building("barracks", 2)],
        units=units or [unit("spear", 10)],
        recruit_orders=[],
        scavenge=scavenge_options or [],
    )

    return VillageContext(
        village=village,
        player=None,
        commands=[],
        quests=quests or [],
        rewards_pending=rewards,
        goal=None,
        recent=[],
        stock={"wood": stock, "clay": stock, "iron": stock},
        pop_free=pop_free,
    )
