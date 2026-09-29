from datetime import UTC, datetime, timedelta

from tests.agents.builders import building, context, scavenge, unit
from tribal_assistant.core.agents.plan import PlanTracker, RulePlanner
from tribal_assistant.core.agents.roles.quartermaster import QuartermasterAgent
from tribal_assistant.core.agents.roles.strategist import StrategistAgent
from tribal_assistant.core.agents.view import ContextView
from tribal_assistant.core.schemas.agent_settings import AgentSettings
from tribal_assistant.core.schemas.plan import PlanStep


def test_tracker_marks_each_step_from_real_state() -> None:
    ctx = context(
        buildings=[building("main", 5), building("wood", 4, queued_level=5), building("stable", 0)],
        units=[unit("spear", 30)],
        scavenge_options=[scavenge(1), scavenge(2, locked=True)],
    )
    steps = [
        PlanStep(kind="build", target="main", amount=5),
        PlanStep(kind="build", target="wood", amount=5),
        PlanStep(kind="build", target="stable", amount=1),
        PlanStep(kind="recruit", target="spear", amount=20),
        PlanStep(kind="unlock_scavenge", target="2", amount=1),
    ]

    statuses = [s.status for s in PlanTracker().evaluate(ctx, steps)]

    assert statuses == ["done", "queued", "blocked", "done", "pending"]


def test_rule_planner_puts_quests_first_and_covers_scavenging() -> None:
    quests = [{"id": "1", "title": "Q", "state": "progress", "can_complete": False,
               "goals": [{"title": "Melhore Mina de ferro", "text": "Expanda Mina de ferro ao nível 3.", "current": 1, "target": 3}]}]
    ctx = context(
        buildings=[building("main", 4), building("wood", 4), building("stone", 4), building("iron", 1), building("barracks", 2)],
        quests=quests,
        scavenge_options=[scavenge(1), scavenge(2, locked=True)],
    )

    summary, steps = RulePlanner().plan(ctx)

    assert steps[0].kind == "build" and steps[0].target == "iron" and steps[0].amount == 3
    assert any(s.kind == "unlock_scavenge" and s.target == "2" for s in steps)
    assert len(steps) <= 12 and summary


def test_plan_needs_refresh_when_empty_finished_or_stuck() -> None:
    assert PlanTracker.needs_refresh([])
    assert PlanTracker.needs_refresh([PlanStep(kind="build", target="main", amount=1, status="done")])
    assert PlanTracker.needs_refresh([PlanStep(kind="build", target="stable", amount=1, status="blocked")])
    assert not PlanTracker.needs_refresh([PlanStep(kind="build", target="main", amount=6, status="pending")])


def test_only_strategist_asks_for_ai_and_only_when_plan_is_stale() -> None:
    settings = AgentSettings()
    ctx = context()
    ctx.plan = [PlanStep(kind="build", target="main", amount=9, status="pending")]
    ctx.plan_refreshed_at = datetime.now(UTC).replace(tzinfo=None)

    assert not StrategistAgent().needs_llm(ctx, settings)

    ctx.plan_refreshed_at -= timedelta(minutes=settings.plan_refresh_minutes + 1)
    assert StrategistAgent().needs_llm(ctx, settings)

    for agent in (QuartermasterAgent(),):
        assert not agent.needs_llm(ctx, settings)


def test_compact_view_is_small_and_role_specific() -> None:
    ctx = context(units=[unit("spear", 12)], scavenge_options=[scavenge(1)])
    ctx.plan = [PlanStep(kind="build", target="main", amount=4, status="pending")]

    raider = ContextView(ctx, 2).render("raider")
    economist = ContextView(ctx, 2).render("economist")

    assert "spear 12" in raider and "Edifícios" not in raider
    assert "Plano:" in economist and "Tropas" not in economist
    assert len(ContextView(ctx, 2).render("strategist")) < 2000
