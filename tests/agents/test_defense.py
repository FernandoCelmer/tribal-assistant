import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import building, context, unit
from tribal_assistant.core.agents.coordination.incoming import (
    DodgePlanner,
    IncomingAttack,
    IncomingWatch,
)
from tribal_assistant.core.agents.coordination.round import VillageRound
from tribal_assistant.core.agents.coordination.threat import ThreatScan
from tribal_assistant.core.agents.proposers.defense import DefenseProposer
from tribal_assistant.core.agents.tools.defense import GetIncoming, SimulateBattle
from tribal_assistant.core.game.actions import GameActions
from tribal_assistant.core.game.incoming import IncomingLabel, TravelClock
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.models.world import WorldPlayer, WorldVillage
from tribal_assistant.core.schemas.agent_settings import AgentSettings


async def _neighbours(session: AsyncSession) -> None:
    session.add_all(
        [
            Village(id=1, game_id="105765", name="Aldeia", coords="500|500", is_own=True),
            WorldPlayer(id=1, name="Frenor", ally_id=7, villages=1, points=300, rank=10),
            WorldPlayer(id=2, name="Amigo", ally_id=7, villages=1, points=5000, rank=2),
            WorldPlayer(id=3, name="Inimigo", ally_id=9, villages=1, points=5000, rank=3),
            WorldVillage(id=10, name="Minha", x=500, y=500, player_id=1, points=300),
            WorldVillage(id=11, name="Do amigo", x=502, y=500, player_id=2, points=5000),
            WorldVillage(id=12, name="Do inimigo", x=503, y=504, player_id=3, points=400),
            WorldVillage(id=20, name="Bárbara perto", x=501, y=500, player_id=0, points=30),
            WorldVillage(id=21, name="Bárbara longe", x=500, y=504, player_id=0, points=30),
        ]
    )
    await session.commit()


def _incoming(origin: str, minutes: float, size: str | None = "small", kind: str = "attack", player: str = "Inimigo") -> dict:
    return {
        "direction": "in",
        "kind": kind,
        "label": IncomingLabel.compose("Ataque", size, player, origin),
        "coords": origin,
        "arrival_at": (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat(),
    }


def _attack(**extra) -> IncomingAttack:
    base = dict(
        kind="attack", arrival_at=datetime.now(UTC) + timedelta(hours=1), minutes_left=60.0, origin="503|504",
        player="Inimigo", player_points=5000, origin_points=400, same_tribe=False, distance=5.0, size="small",
        watchtower=False, first_seen=datetime.now(UTC), unit="axe", tag="infantaria", sent_at=None,
        army={"axe": 260, "light": 35},
    )
    return IncomingAttack(**(base | extra))


async def test_threat_scan_ignores_own_tribe(session: AsyncSession) -> None:
    await _neighbours(session)
    ctx = context()
    ctx.player = {"name": "Frenor"}

    threats = await ThreatScan(session).near(ctx)

    assert [t.player for t in threats] == ["Inimigo"]


async def test_incoming_reads_origin_tag_and_army(session: AsyncSession) -> None:
    await _neighbours(session)
    ctx = context()
    ctx.player = {"name": "Frenor"}
    ctx.commands = [_incoming("503|504", 100), _incoming("502|500", 30, player="Amigo")]

    first, second = await IncomingWatch(session).attacks(ctx)

    assert (second.player, second.origin, second.unit, second.tag) == ("Inimigo", "503|504", "sword", "espadachim")
    assert second.army == {"axe": 260, "light": 35}
    assert not second.same_tribe
    assert first.same_tribe


async def test_first_sighting_is_remembered(session: AsyncSession) -> None:
    await _neighbours(session)
    ctx = context()
    ctx.commands = [_incoming("503|504", 100)]
    watch = IncomingWatch(session)

    (attack,) = await watch.attacks(ctx)
    (again,) = await watch.attacks(ctx, now=datetime.now(UTC) + timedelta(minutes=40))

    assert again.first_seen == attack.first_seen
    assert again.unit == "sword"


def test_dodge_only_when_the_attack_clearly_wins_and_brings_no_noble() -> None:
    planner = DodgePlanner(None, TravelClock())
    weak = context(units=[unit("spear", 20)])
    strong = context(units=[unit("spear", 400), unit("sword", 400)], buildings=[building("wall", 10)])

    assert planner.decide(weak, _attack()).action == "dodge"
    assert planner.decide(strong, _attack()).action == "hold"
    assert planner.decide(weak, _attack(kind="noble")).action == "hold"
    assert planner.decide(weak, _attack(unit="spy", army={"spy": 5})).action == "hold"
    assert planner.decide(weak, _attack(army={})).action == "hold"
    assert planner.decide(weak, _attack(same_tribe=True)).action == "ignore"


def test_dodge_target_keeps_troops_out_until_after_impact() -> None:
    planner = DodgePlanner(None, TravelClock())
    ctx = context(units=[unit("spear", 20)])
    barbarians = [("501|500", 1.0), ("500|504", 4.0), ("500|510", 10.0)]

    assert planner.target(ctx, _attack(minutes_left=60), {"spear": 20}, barbarians) == ("500|504", 72.0)
    assert planner.target(ctx, _attack(minutes_left=600), {"spear": 20}, barbarians) is None


async def test_round_dodges_a_crushing_attack(session: AsyncSession) -> None:
    await _neighbours(session)
    ctx = context(buildings=[building("main", 3), building("wall", 0), building("barracks", 2)], units=[unit("spear", 20)])
    ctx.commands = [_incoming("503|504", 60)]

    decision, _ = await VillageRound(session, AgentSettings(), "d1", True, GameActions()).run(ctx)

    entries = decision.executed + decision.deferred
    dodge = [e for e in entries if e["action"] == "send_farm_attack" and e["source"] == "defense"]
    assert dodge and dodge[0]["arguments"]["target"] == "500|504"
    assert not any(e["action"] == "recruit_units" and e["source"] == "defense" for e in entries)


async def test_round_holds_when_size_is_unknown(session: AsyncSession) -> None:
    await _neighbours(session)
    ctx = context(buildings=[building("main", 3), building("wall", 1), building("barracks", 2)], units=[unit("spear", 10)])
    ctx.commands = [{"direction": "in", "kind": "attack", "label": "Ataque", "coords": None, "arrival_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat()}]

    decision, _ = await VillageRound(session, AgentSettings(), "d2", True, GameActions()).run(ctx)

    assert not any(e["action"] == "send_farm_attack" and e.get("ok") for e in decision.executed)


async def test_preparation_starts_three_days_before_protection_ends(session: AsyncSession) -> None:
    await _neighbours(session)
    ctx = context(
        buildings=[building("main", 5), building("wall", 3), building("hide", 1), building("barracks", 3), building("smith", 1)],
        units=[unit("spear", 30), unit("sword", 0), unit("spy", 0, available=False)],
        stock=5000,
        storage=6000,
        pop_free=300,
    )
    ctx.player = {"name": "Frenor", "protection_until": (datetime.now(UTC) + timedelta(hours=60)).isoformat()}

    decision, insights = await VillageRound(session, AgentSettings(), "d3", True, GameActions()).run(ctx)

    titles = {e["title"] for e in decision.executed + decision.deferred if e["source"] == "defense"}
    assert {"upgrade_building wall", "recruit_units spear"} <= titles
    assert any(i.key == "protection" and "muralha 8" in i.text for i in insights)


def test_troop_goals_add_archers_after_spears_and_swords_and_keep_spies() -> None:
    proposer = DefenseProposer()
    early = context(units=[unit("spear", 30), unit("sword", 10), unit("archer", 0), unit("spy", 1)])
    later = context(units=[unit("spear", 80), unit("sword", 90), unit("archer", 40), unit("spy", 5)])

    assert proposer.troop_goals(early) == {"spear": 20, "sword": 20, "spy": 4}
    assert proposer.troop_goals(later) == {"archer": 20}


def test_hide_grows_with_risk() -> None:
    assert DefenseProposer.hide_level(0, 0, 1000) == 3
    assert DefenseProposer.hide_level(2, 0, 1000) == 5
    assert DefenseProposer.hide_level(3, 1, 4000) == 9


async def test_tools_list_incoming_and_simulate(session: AsyncSession) -> None:
    await _neighbours(session)
    ctx = context(units=[unit("spear", 20)])
    ctx.commands = [_incoming("503|504", 100)]
    box = SimpleNamespace(ctx=ctx, session=session)

    listed = await GetIncoming().run(box, {})
    (row,) = json.loads(listed.text)
    assert (row["origin"], row["tag"], row["decision"]) == ("503|504", "espadachim", "dodge")

    simulated = await SimulateBattle().run(box, {"attacker": {"axe": 100}, "defender": {"spear": 50, "sword": 50}, "wall": 0})
    assert json.loads(simulated.text)["attacker_wins"] is True
    assert (await GetIncoming().run(box, {"village": "1|1"})).ok is False
