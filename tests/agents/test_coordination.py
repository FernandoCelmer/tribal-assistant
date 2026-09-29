from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import building, context, unit
from tribal_assistant.agents.coordination.budget import Budget, Reservation
from tribal_assistant.agents.coordination.constraints import Constraint
from tribal_assistant.agents.coordination.insight import Certainty, Insight
from tribal_assistant.agents.coordination.proposal import Factors, Proposal
from tribal_assistant.agents.coordination.round import VillageRound
from tribal_assistant.agents.coordination.strategy import WEIGHTS, Role
from tribal_assistant.client.actions import GameActions
from tribal_assistant.models.village import Village
from tribal_assistant.models.world import WorldVillage
from tribal_assistant.repositories.coordination import CoordinationRepository
from tribal_assistant.schemas.agent_settings import AgentSettings


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
    assert any("vetado" in e["why"] for e in decision.deferred if e["action"] in ("send_farm_attack", "send_scavenge"))
    assert decision.executed and decision.executed[0]["source"] == "defense"
