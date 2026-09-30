from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import building, context, unit
from tribal_assistant.core.agents.conquest import ConquestPlanner, Escort, Loyalty
from tribal_assistant.core.agents.coordination.constraints import Constraint
from tribal_assistant.core.agents.coordination.proposal import Proposal
from tribal_assistant.core.agents.coordination.round import VillageRound
from tribal_assistant.core.agents.guardrails import Guardrails
from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.tools.conquest import SendNoble
from tribal_assistant.core.game.actions import GameActions
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.models.world import WorldVillage
from tribal_assistant.core.repositories.lessons import LessonRepository
from tribal_assistant.core.schemas.agent_settings import AgentSettings

TARGET = "503|500"


def _ago(hours: float) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


def _noble_village(snob: int = 2, axe: int = 1000, spy: int = 5):
    ctx = context(
        buildings=[building("main", 20), building("snob", 1), building("barracks", 10), building("stable", 5), building("farm", 25)],
        units=[unit("snob", snob, cost=(40000, 50000, 50000, 100)), unit("axe", axe), unit("light", 0), unit("spy", spy), unit("spear", 0)],
        stock=500,
        storage=4000,
    )
    return ctx


async def _world(session: AsyncSession) -> None:
    session.add_all(
        [
            Village(id=1, game_id="105765", name="Aldeia", coords="500|500", is_own=True),
            WorldVillage(id=9, name="Bárbara", x=503, y=500, player_id=0, points=300),
            WorldVillage(id=10, name="Jogador", x=501, y=501, player_id=77, points=900),
        ]
    )
    await session.commit()


async def _intel(session: AsyncSession, **data) -> None:
    await LessonRepository(session).observe(f"target:{TARGET}", "target", f"alvo {TARGET}", "", data)


def test_planner_scouts_then_cleans_then_sends_the_train() -> None:
    knobs = Knobs()
    home = {"snob": 2, "axe": 1000, "spy": 5}

    assert ConquestPlanner.step({}, {}, {"axe": 1000}, 2, knobs).kind == "wait"
    assert ConquestPlanner.step({}, {}, home, 2, knobs).kind == "scout"
    assert ConquestPlanner.step({"scouted_at": _ago(1)}, {}, home, 2, knobs, travelling=True).kind == "wait"

    cleanup = ConquestPlanner.step({"scouted_at": _ago(1)}, {}, home, 2, knobs)
    assert cleanup.kind == "cleanup" and cleanup.squad == {"axe": 800}

    ready = {"scouted_at": _ago(2), "looted_at": _ago(1), "last_result": "green", "defenders_left": 0}
    train = ConquestPlanner.step(ready, {}, home, 2, knobs)
    assert train.kind == "noble" and train.nobles == 2 and train.escort == {"axe": 200}

    single = ConquestPlanner.step(ready, {}, {"snob": 1, "axe": 300}, 2, knobs)
    assert single.kind == "noble" and single.nobles == 1

    dirty = ConquestPlanner.step(ready | {"defenders_left": 3}, {}, home, 2, knobs)
    assert dirty.kind == "cleanup"


def test_single_noble_waits_the_gap_and_loyalty_regenerates() -> None:
    ready = {"scouted_at": _ago(2), "looted_at": _ago(1), "last_result": "green", "defenders_left": 0}
    home = {"snob": 1, "axe": 500}

    recent = ConquestPlanner.step(ready, {"loyalty": 75, "at": _ago(0.1), "noble_at": _ago(0.1)}, home, 2, Knobs())
    assert recent.kind == "wait"

    later = ConquestPlanner.step(ready, {"loyalty": 50, "at": _ago(2), "noble_at": _ago(2)}, home, 2, Knobs())
    assert later.kind == "noble" and later.nobles == 1 and 53 < later.loyalty < 55

    assert Loyalty.now({}, 2) == 100
    assert Loyalty.now({"loyalty": 99, "at": _ago(5)}, 2) == 100
    assert Loyalty.nobles_needed(100, 20) == 5 and Loyalty.nobles_needed(30, 20) == 2
    assert Loyalty.after(30, 2, 20) == 0


def test_train_never_passes_the_knob_nor_the_escort_it_can_cover() -> None:
    ready = {"scouted_at": _ago(2), "looted_at": _ago(1), "last_result": "green", "defenders_left": 0}

    assert ConquestPlanner.step(ready, {}, {"snob": 7, "axe": 5000}, 2, Knobs()).nobles == 5
    assert ConquestPlanner.step(ready, {}, {"snob": 4, "axe": 450}, 2, Knobs()).nobles == 2
    assert ConquestPlanner.step(ready, {}, {"snob": 2, "axe": 100}, 2, Knobs()).kind == "wait"
    assert Escort.per_wave({"axe": 150, "light": 100}, 1, 200) == {"axe": 150, "light": 13}


async def test_noble_guard_only_barbarians_with_nobles_and_escort(session: AsyncSession) -> None:
    await _world(session)
    guard = Guardrails(session, AgentSettings())
    ctx = _noble_village()

    assert await guard.check_noble(ctx, TARGET, 2, {"axe": 200}) is None
    assert "bárbara" in await guard.check_noble(ctx, "501|501", 1, {"axe": 200})
    assert "nobre(s) em casa" in await guard.check_noble(ctx, TARGET, 3, {"axe": 200})
    assert "escolta abaixo" in await guard.check_noble(ctx, TARGET, 1, {"axe": 50})
    assert "em casa para" in await guard.check_noble(ctx, TARGET, 2, {"axe": 600})
    assert "não leva nobre" in await guard.check_noble(ctx, TARGET, 1, {"axe": 200, "snob": 1})
    assert "de 1 a" in await guard.check_noble(ctx, TARGET, 6, {"axe": 200})

    session.add(Village(id=2, game_id="2", name="Nova", coords=TARGET, is_own=True))
    await session.commit()
    assert "bárbara" in await guard.check_noble(ctx, TARGET, 1, {"axe": 200})


async def test_noble_tool_in_simulation_moves_the_train_out(session: AsyncSession) -> None:
    await _world(session)
    ctx = _noble_village()
    box = SimpleNamespace(ctx=ctx, dry_run=True, guard=Guardrails(session, AgentSettings()), session=session)

    outcome = await SendNoble().run(box, {"target": TARGET, "nobles": 2, "escort": {"axe": 200}, "reason": "r"})

    assert outcome.ok and "simulação" in outcome.text
    assert ctx.unit("snob").home == 0 and ctx.unit("axe").home == 600


async def test_conquest_flow_in_simulation(session: AsyncSession) -> None:
    await _world(session)
    settings = AgentSettings()

    scout, _ = await VillageRound(session, settings, "c1", True, GameActions()).run(_noble_village())
    assert any(e["action"] == "send_spy" and e["arguments"]["target"] == TARGET and e["source"] == "conquest" for e in scout.executed)

    await _intel(session, scouted_at=_ago(1), last_result="green")
    clean, _ = await VillageRound(session, settings, "c2", True, GameActions()).run(_noble_village())
    cleanup = [e for e in clean.executed if e["action"] == "send_farm_attack" and e["source"] == "conquest"]
    assert cleanup and cleanup[0]["arguments"]["units"] == {"axe": 800}

    await _intel(session, scouted_at=_ago(1), looted_at=_ago(0.5), last_result="green", defenders_left=0)
    noble, insights = await VillageRound(session, settings, "c3", True, GameActions()).run(_noble_village())
    sent = [e for e in noble.executed if e["action"] == "send_noble"]
    assert sent and sent[0]["ok"] and sent[0]["arguments"]["nobles"] == 2
    assert any(i.key == "conquest" for i in insights)


def test_incoming_attack_holds_the_nobles() -> None:
    veto = Constraint("hold_troops", "ataque chegando", "defense")

    assert veto.violated_by(Proposal("conquest", "send_noble", {"target": TARGET}, ""))
