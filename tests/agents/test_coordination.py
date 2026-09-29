from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import building, context, unit
from tribal_assistant.core.agents.coordination.budget import Budget, Reservation
from tribal_assistant.core.agents.coordination.constraints import Constraint
from tribal_assistant.core.agents.coordination.insight import Certainty, Insight
from tribal_assistant.core.agents.coordination.proposal import Factors, Proposal
from tribal_assistant.core.agents.coordination.round import VillageRound
from tribal_assistant.core.agents.coordination.strategy import WEIGHTS, Role
from tribal_assistant.core.game.actions import GameActions
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.models.world import WorldVillage
from tribal_assistant.core.repositories.coordination import CoordinationRepository
from tribal_assistant.core.schemas.agent_settings import AgentSettings


def test_old_information_weighs_less() -> None:
    fresh = Insight("t", "alvo vazio", Certainty.HYPOTHESIS, datetime.now(UTC).replace(tzinfo=None), 0.8)
    old = Insight("t", "alvo vazio", Certainty.HYPOTHESIS, datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24), 0.8)

    assert fresh.weight(24) > 0.79
    assert 0.39 < old.weight(24) < 0.41


def test_reserved_resources_are_not_free() -> None:
    ctx = context(stock=5000, storage=8000)
    budget = Budget(ctx)
    budget.reserve(Reservation("expansion", "strategic", "nobre", {"wood": 3000}))

    assert budget.free()["wood"] == 2000
    assert budget.free("expansion")["wood"] == 5000
    assert not budget.affordable({"wood": 2500})
    assert budget.affordable({"wood": 2500}, purpose="expansion")


def test_emergency_weights_put_risk_above_economic_return() -> None:
    growth = Proposal("infrastructure", "upgrade_building", {"building": "wood"}, "", factors=Factors(impact=0.9, opportunity=0.5))
    defense = Proposal("defense", "upgrade_building", {"building": "wall"}, "", factors=Factors(urgency=0.9, risk_avoided=0.9))

    assert WEIGHTS[Role.GROWTH].score(growth.factors) > WEIGHTS[Role.GROWTH].score(defense.factors) * 0.5
    assert WEIGHTS[Role.EMERGENCY].score(defense.factors) > WEIGHTS[Role.EMERGENCY].score(growth.factors)


def test_hold_troops_veto_blocks_raids_and_scavenging() -> None:
    veto = Constraint("hold_troops", "ataque chegando", "defense")

    assert veto.violated_by(Proposal("attack", "send_farm_attack", {"target": "1|1"}, ""))
    assert veto.violated_by(Proposal("attack", "send_scavenge", {"option_id": 1}, ""))
    assert not veto.violated_by(Proposal("infrastructure", "upgrade_building", {"building": "wall"}, ""))


async def _world(session: AsyncSession) -> None:
    session.add_all(
        [
            Village(id=1, game_id="105765", name="Aldeia", coords="500|500", is_own=True),
            WorldVillage(id=9, name="Bárbara", x=503, y=500, player_id=0, points=30),
        ]
    )
    await session.commit()


async def test_round_builds_storage_before_it_fills_and_explains_deferrals(session: AsyncSession) -> None:
    await _world(session)
    ctx = context(
        buildings=[building("main", 3), building("wood", 4), building("storage", 2, cost=200), building("barracks", 2), building("wall", 0)],
        units=[unit("spear", 10)],
        stock=1900,
        storage=2000,
    )
    ctx.village.wood_prod = 100

    decision, insights = await VillageRound(session, AgentSettings(), "r1", True, GameActions()).run(ctx)

    done = [e["title"] for e in decision.executed if e["ok"]]
    assert done[:2] == ["upgrade_building storage", "upgrade_building main"]
    assert decision.mode == Role.GROWTH
    assert any(i.certainty == Certainty.ESTIMATE and i.key == "storage_full" for i in insights)
    assert (await CoordinationRepository(session).latest())[0].mode == "growth"


async def test_incoming_attack_switches_to_emergency_and_keeps_troops_home(session: AsyncSession) -> None:
    await _world(session)
    ctx = context(buildings=[building("main", 3), building("wall", 1), building("barracks", 2)], units=[unit("spear", 10)])
    ctx.commands = [{"direction": "in", "kind": "attack", "arrival_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat()}]

    decision, _ = await VillageRound(session, AgentSettings(), "r2", True, GameActions()).run(ctx)

    assert decision.mode == Role.EMERGENCY
    assert not any(e["action"] == "send_farm_attack" and e.get("ok") for e in decision.executed)
    assert all("vetado" in e["why"] for e in decision.deferred if e["action"] in ("send_farm_attack", "send_scavenge"))
    assert not any(e["action"] in ("send_farm_attack", "send_scavenge") for e in decision.executed)
    assert decision.executed and decision.executed[0]["source"] == "defense"


def test_role_rules_pick_defense_offensive_support_expansion_or_growth() -> None:
    from tribal_assistant.core.agents.coordination.roles import RoleSelector
    from tribal_assistant.core.agents.coordination.threat import Threat

    ctx = context(units=[unit("spear", 10), unit("light", 30)])
    near = [Threat("Vizinho", 5000, 3.2)]

    assert RoleSelector.decide(ctx, {"dangerous": near, "protection_hours": 10})[0] == Role.DEFENSE
    assert RoleSelector.decide(ctx, {"dangerous": near, "protection_hours": 90})[0] != Role.DEFENSE
    assert RoleSelector.decide(ctx, {"others_under_attack": [2], "own_villages": 2})[0] == Role.SUPPORT
    assert RoleSelector.decide(ctx, {"good_targets": 4})[0] == Role.OFFENSIVE
    assert RoleSelector.decide(context(), {})[0] == Role.GROWTH

    rich = context(buildings=[building("main", 20), building("smith", 18), building("market", 8)])
    assert RoleSelector.decide(rich, {})[0] == Role.EXPANSION


async def test_role_switches_only_after_it_repeats(session: AsyncSession) -> None:
    from tribal_assistant.core.agents.coordination.roles import RoleSelector

    selector = RoleSelector(session)
    ctx = context()

    assert await selector._confirm(ctx, Role.GROWTH, Role.OFFENSIVE) == Role.GROWTH
    assert await selector._confirm(ctx, Role.GROWTH, Role.OFFENSIVE) == Role.GROWTH
    assert await selector._confirm(ctx, Role.GROWTH, Role.OFFENSIVE) == Role.OFFENSIVE
    assert await selector._confirm(ctx, Role.GROWTH, Role.DEFENSE) == Role.DEFENSE


def test_base_reserve_does_not_block_buildings() -> None:
    ctx = context(stock=300, storage=2810)
    budget = Budget(ctx)
    budget.reserve(Reservation("base", "base", "mínimo", {"wood": 281, "clay": 281, "iron": 281}, applies_to=("recruit_units",)))

    assert budget.affordable({"wood": 231, "clay": 219, "iron": 205}, action="upgrade_building")
    assert not budget.affordable({"wood": 231, "clay": 219, "iron": 205}, action="recruit_units")
