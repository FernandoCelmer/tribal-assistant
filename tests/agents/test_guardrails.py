from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import building, context, unit
from tribal_assistant.agents.guardrails import Guardrails
from tribal_assistant.models.world import WorldVillage
from tribal_assistant.schemas.agent_settings import AgentSettings


def test_upgrade_allowed_when_affordable(session: AsyncSession) -> None:
    assert Guardrails(session, AgentSettings()).check_upgrade(context(), "wood") is None


def test_upgrade_refused_when_queue_full(session: AsyncSession) -> None:
    ctx = context(buildings=[building("main", 3, queued_level=4), building("wall", 0, queued_level=1), building("wood", 4)])

    assert Guardrails(session, AgentSettings()).check_upgrade(ctx, "wood") == "fila de construção cheia"


def test_upgrade_refused_without_resources_or_requirements(session: AsyncSession) -> None:
    guard = Guardrails(session, AgentSettings())

    assert "recursos" in guard.check_upgrade(context(stock=50), "wood")
    assert "requisitos" in guard.check_upgrade(context(buildings=[building("stable", 0)]), "stable")


def test_recruit_respects_reserve_budget_and_population(session: AsyncSession) -> None:
    guard = Guardrails(session, AgentSettings())

    plan = guard.plan_recruit(context(stock=1000, storage=2000, pop_free=100), "spear", 50)
    assert plan.count == 8

    assert guard.plan_recruit(context(pop_free=3), "spear", 50).count == 3
    assert guard.plan_recruit(context(units=[unit("axe", available=False)]), "axe", 5).refusal


async def test_attack_only_on_known_barbarians_in_radius(session: AsyncSession) -> None:
    session.add_all(
        [
            WorldVillage(id=1, name="Bárbara", x=503, y=500, player_id=0, points=30),
            WorldVillage(id=2, name="Jogador", x=502, y=500, player_id=77, points=300),
            WorldVillage(id=3, name="Longe", x=560, y=500, player_id=0, points=30),
        ]
    )
    await session.commit()

    guard = Guardrails(session, AgentSettings())
    ctx = context(units=[unit("spear", 10)])

    assert await guard.check_attack(ctx, "503|500", {"spear": 5}) is None
    assert "bárbara" in await guard.check_attack(ctx, "502|500", {"spear": 5})
    assert "limite" in await guard.check_attack(ctx, "560|500", {"spear": 5})
    assert "só há" in await guard.check_attack(ctx, "503|500", {"spear": 50})
