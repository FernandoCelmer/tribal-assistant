import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import context
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import Knobs, Metrics, Tuner
from tribal_assistant.core.agents.proposers.social import SocialProposer
from tribal_assistant.core.agents.social.ledger import MENTOR, SocialLedger
from tribal_assistant.core.agents.social.writer import Written
from tribal_assistant.core.game.wander import SAFE_SCREENS
from tribal_assistant.core.models.agent import AgentDecision
from tribal_assistant.core.models.lesson import Lesson
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.models.world import WorldAlly, WorldPlayer, WorldVillage
from tribal_assistant.core.schemas.agent_settings import AgentSettings

ME = {"name": "Jogador", "world": "br144", "points": 400, "rank": 900, "villages": 1, "incomings": 0}


def moment() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Social:
    async def inbox(self, village_id):
        return []

    async def buddies(self, village_id):
        return {"friends": [], "outgoing": [], "incoming": []}


class Actions:
    def __init__(self) -> None:
        self.social = Social()


class Writer:
    def __init__(self) -> None:
        self.reasons: list[str] = []

    async def intro(self, facts, card, reason):
        self.reasons.append(reason)
        return Written(text="Oi! Mandei a candidatura e queria me apresentar.", subject="Candidatura")


def view(session: AsyncSession, knobs: dict | None = None) -> CoordinationView:
    ctx = context()
    ctx.player = dict(ME)
    result = CoordinationView(ctx, session, AgentSettings(), Actions(), False, Role.GROWTH, Role.GROWTH, None)
    result.knobs = Knobs(knobs or {})
    return result


async def world(session: AsyncSession) -> None:
    session.add_all(
        [
            Village(id=1, game_id="105765", name="Aldeia", coords="500|500", is_own=True),
            WorldPlayer(id=10, name="Vizinho", ally_id=0, villages=1, points=350, rank=5),
            WorldPlayer(id=11, name="Parado", ally_id=0, villages=1, points=26, rank=900),
            WorldPlayer(id=12, name="Lider", ally_id=239, villages=3, points=9000, rank=1),
            WorldVillage(id=100, name="a", x=503, y=500, player_id=10, points=350),
            WorldVillage(id=101, name="b", x=502, y=502, player_id=11, points=26),
            WorldVillage(id=102, name="c", x=560, y=560, player_id=12, points=9000),
            WorldAlly(id=239, name="Larga", tag="LARGA3", members=20, villages=40, points=90000, all_points=90000, rank=3),
        ]
    )
    await session.commit()


async def test_pace_comes_from_any_pair_of_photos_an_hour_apart(session: AsyncSession) -> None:
    ledger = SocialLedger(session)
    assert await ledger.rates("players", {"1": 100}, 1, 24) == {}

    row = await ledger.repo.get("snapshot:players")
    old = (moment() - timedelta(hours=2)).isoformat()
    row.data = json.dumps({"history": [{"at": old, "points": {"1": 100, "2": 50}}]})
    await session.commit()

    assert await ledger.rates("players", {"1": 160, "2": 52}, 1, 24) == {"1": 30.0, "2": 1.0}
    assert len(json.loads((await ledger.repo.get("snapshot:players")).data)["history"]) == 2


async def test_old_single_photo_format_still_counts(session: AsyncSession) -> None:
    ledger = SocialLedger(session)
    await ledger.repo.observe("snapshot:allies", "social", "pontos", "", {"points": {"7": 1000}, "at": (moment() - timedelta(hours=3)).isoformat()})

    assert await ledger.rates("allies", {"7": 1300}, 1, 24) == {"7": 100.0}


async def test_neighbours_without_history_are_judged_by_the_world_data(session: AsyncSession) -> None:
    await world(session)
    found = await SocialLedger(session).active_neighbours(Knobs(), {"Jogador"}, 400)

    assert [n["name"] for n in found] == ["Vizinho"]
    assert found[0]["rate"] is None and "no ritmo da conta" in found[0]["why"]


async def test_measured_pace_wins_over_the_estimate(session: AsyncSession) -> None:
    await world(session)
    ledger = SocialLedger(session)
    old = (moment() - timedelta(hours=2)).isoformat()
    await ledger.repo.observe("snapshot:players", "social", "pontos", "", {"history": [{"at": old, "points": {"10": 349, "11": 6}}]})

    found = await ledger.active_neighbours(Knobs(), set(), 400)
    assert [(n["name"], n["rate"]) for n in found] == [("Parado", 10.0)]


async def test_ledger_rebuilds_applications_and_mentor_from_old_decisions(session: AsyncSession) -> None:
    await world(session)
    applied = moment() - timedelta(hours=5)
    session.add(AgentDecision(village_id=None, run_id="r", agent="diplomacy", action="apply_to_tribe", arguments=json.dumps({"ally_id": "239", "text": "oi"}), ok=True, dry_run=False, created_at=applied, updated_at=applied))
    session.add(AgentDecision(village_id=None, run_id="r", agent="diplomacy", action="apply_to_tribe", arguments=json.dumps({"ally_id": "555"}), ok=True, dry_run=True, created_at=applied, updated_at=applied))
    session.add(Lesson(key="action:accept_mentor:ok", topic="action", title="accept_mentor funciona", data=json.dumps({"last_args": {"mentor_id": "3", "name": "Mestre"}}), first_seen=applied, last_seen=applied))
    await session.commit()
    ledger = SocialLedger(session)

    assert await ledger.rebuild() == ["candidatura LARGA3", "mentor Mestre"]
    assert await ledger.rebuild() == []
    [application] = await ledger.applications()
    assert (application["ally_id"], application["tag"], application["status"]) == ("239", "LARGA3", "pendente")
    assert application["first_seen"] == applied
    assert (await ledger.get(MENTOR))["name"] == "Mestre"


async def test_social_follows_up_the_application_and_befriends_an_active_neighbour(session: AsyncSession) -> None:
    await world(session)
    applied = moment() - timedelta(hours=5)
    session.add(AgentDecision(village_id=None, run_id="r", agent="diplomacy", action="apply_to_tribe", arguments=json.dumps({"ally_id": "239", "tag": "LARGA3"}), ok=True, dry_run=False, created_at=applied, updated_at=applied))
    await session.commit()
    writer = Writer()
    current = view(session)

    items = [p for p in await SocialProposer(writer).propose(current) if p.action != "browse_game"]

    assert [(p.action, p.arguments.get("name") or p.arguments.get("to")) for p in items] == [("add_friend", "Vizinho"), ("send_mail", "Lider")]
    assert items[1].arguments["kind"] == "intro_leader" and "LARGA3" in writer.reasons[0]
    insight = next(i for i in current.insights if i.key == "social")
    assert insight.text.startswith("social: 3 proposta(s)") and "candidatura LARGA3" in insight.text


async def test_social_says_why_it_proposed_nothing(session: AsyncSession) -> None:
    session.add(Village(id=1, game_id="105765", name="Aldeia", coords="500|500", is_own=True))
    await session.commit()
    current = view(session)

    assert [p.action for p in await SocialProposer(Writer()).propose(current)] == ["browse_game"]
    insight = next(i for i in current.insights if i.key == "social")
    assert insight.text.startswith("social: 1 proposta(s)")
    assert "vizinho ativo" in insight.text and "caixa lida: 0 conversa(s)" in insight.text

    again = view(session)
    await SocialProposer(Writer()).propose(again)
    text = next(i for i in again.insights if i.key == "social").text
    assert "caixa lida há pouco" in text and "sem candidatura pendente" in text and "passeio pelo jogo feito há pouco" in text


async def test_long_social_silence_loosens_the_social_knobs() -> None:
    changes = {name: value for name, value, _ in Tuner.plan(Knobs(), Metrics(rounds=20, social_idle=1.0))}

    assert changes["cooldown.outreach"] < 2 and changes["cooldown.friend_request"] < 4 and changes["cooldown.browse"] < 0.5
    assert changes["social.active_growth"] < 5 and changes["social.snapshot_hours"] < 1
    assert changes["social.neighbour_radius"] > 10 and changes["social.first_contacts_per_day"] > 5

    calm = {name: value for name, value, _ in Tuner.plan(Knobs({"cooldown.outreach": 1}), Metrics(rounds=20, social_idle=0.1))}
    assert 1 < calm["cooldown.outreach"] <= 2


async def test_social_browses_rankings_neighbours_and_tribes(session: AsyncSession) -> None:
    await world(session)
    current = view(session, {"browse.pages": 30})

    [browse] = [p for p in await SocialProposer(Writer()).propose(current) if p.action == "browse_game"]

    labels = [stop["label"] for stop in browse.arguments["stops"]]
    assert "ranking de jogadores" in labels and "perfil de Vizinho" in labels
    assert all(stop["screen"] in SAFE_SCREENS for stop in browse.arguments["stops"])
