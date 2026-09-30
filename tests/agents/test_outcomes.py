import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import building, context
from tribal_assistant.core.agents.coordination.budget import Reservation
from tribal_assistant.core.agents.coordination.constraints import Constraint
from tribal_assistant.core.agents.coordination.coordinator import Coordinator
from tribal_assistant.core.agents.coordination.outcomes import Evidence, Outcomes, RoundRecord
from tribal_assistant.core.agents.coordination.proposal import Factors, Proposal
from tribal_assistant.core.agents.coordination.round import VillageRound
from tribal_assistant.core.agents.coordination.strategy import SPECIALISTS, Role
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import Knobs, KnobStore, Metrics, Tuner
from tribal_assistant.core.game.actions import GameActions
from tribal_assistant.core.models.agent import AgentDecision
from tribal_assistant.core.models.coordination import CoordinationRound
from tribal_assistant.core.models.report import Report
from tribal_assistant.core.models.snapshot import VillageSnapshot
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.schemas.agent_settings import AgentSettings

T0 = datetime(2026, 9, 29, 12, 0)


def entry(source: str, action: str, ok: bool = True, result: str = "feito", **extra) -> dict:
    return {"source": source, "action": action, "title": f"{action} {extra.get('title', '')}".strip(), "ok": ok, "result": result, "arguments": extra.get("arguments", {}), "factors": extra.get("factors", {}), "exploration": extra.get("exploration", False)}


def record(entries: list[dict], at: datetime = T0, village: int = 1, mode: str = "growth") -> RoundRecord:
    return RoundRecord(village, at, {"mode": mode, "executed": entries})


class Rng:
    def __init__(self, roll: float) -> None:
        self.roll = roll

    def random(self) -> float:
        return self.roll

    def choice(self, items):
        return items[0]


def test_value_follows_what_happened_afterwards() -> None:
    evidence = Evidence(
        snapshots={1: [(T0 - timedelta(minutes=5), 100, 10), (T0 + timedelta(hours=1), 130, 10)]},
        reports={"501|500": [(T0 + timedelta(minutes=30), "green", 400)], "502|500": [(T0 + timedelta(minutes=30), "red", 0)]},
    )
    outcomes = Outcomes(evidence)

    assert outcomes.value(entry("economy", "upgrade_building"), 1, T0) == 1.0
    assert outcomes.value(entry("recruitment", "recruit_units"), 1, T0) == 0.25
    assert outcomes.value(entry("attack", "send_farm_attack", arguments={"target": "501|500"}), 1, T0) == 1.0
    assert outcomes.value(entry("attack", "send_farm_attack", arguments={"target": "502|500"}), 1, T0) == -1.0
    assert outcomes.value(entry("steward", "open_daily_bonus"), 1, T0) == 0.625
    assert outcomes.value(entry("social", "send_mail", ok=False, result="RECUSADO: limite"), 1, T0) == -1.0
    assert outcomes.value(entry("social", "send_mail", ok=False, result="erro do jogo"), 1, T0) == -0.5
    assert outcomes.value(entry("economy", "upgrade_building", result="(simulação) subir"), 1, T0) is None


def test_specialists_that_yield_more_get_a_bigger_bonus_and_the_rest_walk_back() -> None:
    records = [record([entry("economy", "upgrade_building"), entry("social", "send_mail", ok=False, result="RECUSADO: x"), entry("steward", "use_item")]) for _ in range(4)]
    metrics = Metrics(rounds=20, yields=Outcomes(Evidence(snapshots={1: [(T0 - timedelta(minutes=1), 1, 0), (T0 + timedelta(hours=1), 5, 0)]})).yields(records))

    assert metrics.yields == {"economy": 1.0, "social": -1.0, "steward": 0.625}
    changes = {name: value for name, value, _ in Tuner.plan(Knobs({"bonus.defense": 1.5}), metrics)}
    assert changes["bonus.economy"] > 1.0 and changes["bonus.social"] < 1.0
    assert changes["bonus.steward"] > 1.0 and changes["bonus.defense"] < 1.5

    even = {name: value for name, value, _ in Tuner.plan(Knobs({"bonus.economy": 1.3}), Metrics(rounds=20, yields={"economy": 0.5, "attack": 0.55}))}
    assert 1.0 <= even["bonus.economy"] < 1.3 and "bonus.attack" not in even


def test_learned_knobs_have_no_bounds_but_stay_positive_and_shares_stay_fractions() -> None:
    assert Knobs.step("bonus.economy", 1.95, +1) > 2.0
    assert 0 < Knobs.step("bonus.economy", 0.01, -1) < 0.01
    assert Knobs.step("coordinator.explore_rate", 0.95, +1) <= 1.0


def test_factor_weights_learn_from_the_proposals_they_favoured() -> None:
    good = [entry("attack", "send_farm_attack", arguments={"target": "501|500"}, factors={"opportunity": 0.9}) for _ in range(4)]
    bad = [entry("economy", "upgrade_building", ok=False, result="RECUSADO: x", factors={"opportunity": 0.1}) for _ in range(4)]
    evidence = Evidence(reports={"501|500": [(T0 + timedelta(minutes=10), "green", 300)]})
    gaps = Outcomes(evidence).factor_gaps([record(good + bad)])

    assert gaps["growth.opportunity"] == 2.0
    changes = {name: value for name, value, _ in Tuner.plan(Knobs(), Metrics(rounds=20, factor_gaps=gaps))}
    assert changes["weight.growth.opportunity"] > 0.2
    assert "weight.growth.urgency" not in changes


def test_repeated_rounds_are_measured_and_the_streak_is_counted() -> None:
    same = [entry("economy", "upgrade_building", title="wood")]
    records = [record(same, T0 + timedelta(minutes=i)) for i in range(4)] + [record([entry("attack", "send_scavenge")], T0 + timedelta(minutes=9))]

    assert Outcomes.repetition(records, 3) == 0.8
    assert Outcomes.streak([r.data for r in reversed(records[:4])]) == 4
    assert Outcomes.streak([{"executed": []}]) == 0


def test_exploration_rate_rises_with_repetition_and_falls_when_it_does_worse() -> None:
    up = dict((n, v) for n, v, _ in Tuner.plan(Knobs(), Metrics(rounds=20, repetition=0.7)))
    down = dict((n, v) for n, v, _ in Tuner.plan(Knobs(), Metrics(rounds=20, repetition=0.7, explored=5, explore_gap=-0.5)))

    assert up["coordinator.explore_rate"] > 0.1
    assert down["coordinator.explore_rate"] < 0.1


def test_explorations_are_compared_with_the_usual_choices() -> None:
    records = [record([entry("economy", "use_item", exploration=True), entry("economy", "use_item", ok=False, result="erro")])]
    assert Outcomes().explore(records) == (1, 1.125)


def test_every_specialist_has_a_bonus_knob() -> None:
    assert {p.key for p in (c() for c in VillageRound.PROPOSERS)} == set(SPECIALISTS)
    assert all(f"bonus.{key}" in Knobs.SPECS for key in SPECIALISTS)


def _view(session: AsyncSession, dry_run: bool = False) -> CoordinationView:
    ctx = context(buildings=[building("main", 3), building("wood", 4), building("clay", 4)], stock=5000, storage=8000)
    view = CoordinationView(ctx, session, AgentSettings(), GameActions(), dry_run, Role.GROWTH, Role.GROWTH, None)
    view.knobs = Knobs({"coordinator.explore_rate": 0.5, "bonus.steward": 2.0})
    return view


def _proposals() -> list[Proposal]:
    return [
        Proposal("economy", "upgrade_building", {"building": "wood", "reason": "madeira"}, "madeira", factors=Factors(impact=0.9)),
        Proposal("attack", "send_farm_attack", {"target": "501|500", "reason": "saque"}, "saque", factors=Factors(impact=0.5)),
        Proposal("steward", "use_item", {"key": "x", "reason": "item"}, "item", factors=Factors(impact=0.2)),
    ]


async def test_exploration_promotes_a_viable_proposal_and_says_so(session: AsyncSession) -> None:
    order = []

    async def execute(proposal: Proposal) -> tuple[bool, str]:
        order.append(proposal.title())
        return True, "feito"

    veto = Constraint("block_actions", "ataque chegando", "defense", None, ("send_farm_attack",))
    decision = await Coordinator(_view(session), Rng(0.0)).run(_proposals(), [veto], [], execute)
    data = decision.to_dict([])

    assert order[0] == "use_item x" and "send_farm_attack 501|500" not in order
    assert data["exploration"]["title"] == "use_item x" and data["exploration"]["instead_of"] == "upgrade_building wood"
    assert data["executed"][0]["exploration"] is True and data["executed"][1]["exploration"] is False
    assert data["learned"]["bonus"]["steward"] == 1.4 and data["executed"][0]["bonus"] == 1.4
    assert "exploração" in decision.summary()


async def test_no_exploration_above_the_rate_or_in_read_only_mode(session: AsyncSession) -> None:
    async def execute(proposal: Proposal) -> tuple[bool, str]:
        return True, "feito"

    assert (await Coordinator(_view(session), Rng(0.9)).run(_proposals(), [], [], execute)).exploration is None
    assert (await Coordinator(_view(session, dry_run=True), Rng(0.0)).run(_proposals(), [], [], execute)).exploration is None


async def test_store_measures_yields_repetition_and_social_idle(session: AsyncSession) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    session.add(Village(id=1, game_id="105765", name="Aldeia", coords="500|500", is_own=True))
    session.add_all([VillageSnapshot(village_id=1, taken_at=now - timedelta(hours=3), points=100, wood=0, clay=0, iron=0, storage=0, pop_current=0, pop_max=0, wood_prod=0, clay_prod=0, iron_prod=0, troops_home=0, troops_total=0)])
    session.add(VillageSnapshot(village_id=1, taken_at=now - timedelta(minutes=5), points=150, wood=0, clay=0, iron=0, storage=0, pop_current=0, pop_max=0, wood_prod=0, clay_prod=0, iron_prod=0, troops_home=0, troops_total=0))
    session.add(Report(game_id="r1", title="saque", category="attack", result="green", received_at=now - timedelta(hours=1), target_coords="501|500", haul_total=300))
    executed = [entry("economy", "upgrade_building", title="wood"), entry("attack", "send_farm_attack", title="501|500", arguments={"target": "501|500"})]
    for minutes in (120, 110, 100, 90):
        at = now - timedelta(minutes=minutes)
        session.add(CoordinationRound(run_id="r", village_id=1, created_at=at, role="growth", mode="growth", goal="", data=json.dumps({"mode": "growth", "executed": executed})))
    session.add(AgentDecision(village_id=None, run_id="r", agent="social", action="add_friend", ok=True, dry_run=False, created_at=now - timedelta(hours=3), updated_at=now))
    await session.commit()

    metrics = await KnobStore(session).metrics()

    assert metrics.yields == {"economy": 1.0, "attack": 1.0}
    assert metrics.repetition == 1.0
    assert metrics.social_idle == 0.5


def test_scouting_and_scavenging_count_as_yield():
    at = datetime(2026, 9, 30, 12, 0)
    evidence = Evidence(reports={"487|752": [(at + timedelta(minutes=40), "blue", 0)]})

    assert evidence.confirm({"action": "send_spy", "arguments": {"target": "487|752"}}, 1, at) == 1.0
    assert evidence.confirm({"action": "send_scavenge", "arguments": {}}, 1, at) == 1.0


async def test_an_idle_reservation_already_in_stock_is_dropped(session: AsyncSession) -> None:
    coordinator = Coordinator(_view(session), Rng(0.9))
    idle = Reservation("research:axe", "strategic", "pesquisa", {"wood": 700, "clay": 840, "iron": 820})
    owned = Reservation("plan:wall", "operation", "muralha", {"wood": 300})
    base = Reservation("base", "base", "reserva", {"wood": 100})
    proposals = [Proposal("infrastructure", "upgrade_building", {"building": "wall"}, "", purpose="plan:wall")]

    kept = coordinator.live([idle, owned, base], proposals)

    assert [r.purpose for r in kept] == ["plan:wall", "base"]
