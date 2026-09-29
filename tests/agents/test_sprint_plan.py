from datetime import UTC, datetime, timedelta

from tests.agents.builders import building, context, unit
from tribal_assistant.core.agents.noble import Candidate, NobleReadiness, NobleTarget
from tribal_assistant.core.agents.pacing import BuildPacing
from tribal_assistant.core.agents.plan import RulePlanner
from tribal_assistant.core.agents.quests import QuestRules
from tribal_assistant.core.agents.roles.quartermaster import QuartermasterAgent


def _quest(title: str, text: str, target: int = 1, can_complete: bool = False) -> dict:
    return {"id": title, "title": title, "state": "progress", "can_complete": can_complete,
            "goals": [{"title": title, "text": text, "current": 0, "target": target}]}


def _builds(steps) -> dict[str, int]:
    return {s.target: s.amount for s in steps if s.kind == "build"}


def test_statue_comes_right_after_barracks_one() -> None:
    ctx = context(buildings=[building("main", 3), building("barracks", 1), building("statue", 0), building("wood", 2)])

    _, steps = RulePlanner().plan(ctx)

    assert (steps[0].target, steps[0].amount) == ("statue", 1)


def test_no_statue_before_barracks() -> None:
    ctx = context(buildings=[building("main", 2), building("barracks", 0), building("statue", 0)])

    assert "statue" not in _builds(RulePlanner().plan(ctx)[1])


def test_wall_and_hide_quests_are_followed_up_to_level_three() -> None:
    quests = [
        _quest("O Guerreiro mais Forte", "Construa Muralha no edifício principal (0/1)."),
        _quest("Um lugar seguro", "Expanda Esconderijo ao nível 3."),
        _quest("Muralha forte", "Expanda Muralha ao nível 5."),
    ]
    ctx = context(buildings=[building("main", 5), building("barracks", 1), building("wall", 0), building("hide", 1)], quests=quests)

    builds = _builds(RulePlanner().plan(ctx)[1])

    assert builds["wall"] == 1
    assert builds["hide"] == 3


def test_militia_quest_is_ignored_and_never_completed() -> None:
    militia = _quest("Milícia", "Ative a milícia na Fazenda nível 1.", can_complete=True)

    assert QuestRules.forbidden(militia)
    assert QuestRules.building_goals([militia], {"farm": 0}) == []
    assert not QuestRules.forbidden(_quest("Bosque", "Expanda Bosque ao nível 3."))
    assert QuartermasterAgent.mission.count("milícia") >= 1


def test_iron_stays_three_below_until_stable_and_wood_leads() -> None:
    before = {"wood": 6, "stone": 5, "iron": 2}
    assert BuildPacing.pits(before) == ["stone", "wood"]
    assert "iron" in BuildPacing.pits({"wood": 6, "stone": 6, "iron": 2})
    assert BuildPacing.pits({"wood": 4, "stone": 4, "iron": 1}) == ["wood"]
    assert "iron" in BuildPacing.pits({"wood": 6, "stone": 6, "iron": 5, "stable": 1})


def test_planner_never_raises_iron_close_to_wood_before_stable() -> None:
    ctx = context(buildings=[building("main", 5), building("barracks", 1), building("wood", 5), building("stone", 5), building("iron", 2)])

    builds = _builds(RulePlanner().plan(ctx)[1])

    assert "iron" not in builds
    assert builds["wood"] == 6


def test_main_building_stops_at_ten_until_stable_three() -> None:
    assert BuildPacing.main_cap({"main": 10, "stable": 2}) == 10
    assert BuildPacing.main_cap({"main": 10, "stable": 3}) == 20

    ctx = context(buildings=[building("main", 10), building("barracks", 4), building("smith", 5), building("stable", 0), building("storage", 7)])
    builds = _builds(RulePlanner().plan(ctx)[1])

    assert "main" not in builds
    assert builds["barracks"] == 5


def test_storage_grows_for_the_stable_gate() -> None:
    ctx = context(
        buildings=[building("main", 10), building("barracks", 5), building("smith", 5), building("stable", 0, cost=3000), building("storage", 5)],
        storage=3000,
    )

    builds = _builds(RulePlanner().plan(ctx)[1])

    assert builds["storage"] == 6 and builds["stable"] == 1


def test_barracks_and_stable_follow_main_after_protection() -> None:
    assert BuildPacing.military_due({"main": 16, "barracks": 7, "stable": 5}, protected=False) == ["barracks", "stable"]
    assert BuildPacing.military_due({"main": 16, "barracks": 9, "stable": 7}, protected=False) == []
    assert BuildPacing.military_due({"main": 16, "barracks": 5, "stable": 3}, protected=True) == []


def test_protection_end_calls_for_wall_eight() -> None:
    ctx = context(buildings=[building("main", 10), building("barracks", 5), building("wall", 3)])
    ctx.player = {"protection_until": (datetime.now(UTC) + timedelta(hours=60)).isoformat()}

    assert _builds(RulePlanner().plan(ctx)[1]).get("wall") == 4

    ctx.player = {"protection_until": (datetime.now(UTC) + timedelta(hours=90)).isoformat()}
    assert "wall" not in _builds(RulePlanner().plan(ctx)[1])


def test_noble_needs_farm_and_a_real_army() -> None:
    path = [building("main", 20), building("smith", 20), building("market", 10)]

    assert "farm 24" in NobleReadiness.missing(context(buildings=[*path, building("farm", 20)], units=[unit("spear", 3000)]))
    assert NobleReadiness.missing(context(buildings=[*path, building("farm", 24)], units=[unit("spear", 100)]))
    assert NobleReadiness.ready(context(buildings=[*path, building("farm", 24)], units=[unit("spear", 3000)]))


def test_first_noble_target_prefers_known_farm_bonus_then_big_barbarian() -> None:
    known = Candidate("1|1", 300, 4.0, 0, True)
    bonus = Candidate("2|2", 200, 6.0, 4, True)
    big = Candidate("3|3", 2500, 3.0)

    assert NobleTarget.pick([known, bonus, big]) == bonus
    assert NobleTarget.pick([known, big]) == known
    assert NobleTarget.pick([big, Candidate("4|4", 900, 2.0)]) == big
    assert NobleTarget.pick([Candidate("9|9", 5000, 30.0)]) is None
