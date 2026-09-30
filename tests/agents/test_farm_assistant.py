import json
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import context, unit
from tribal_assistant.core.agents.guardrails import Guardrails
from tribal_assistant.core.agents.knobs import Knobs, Metrics, Tuner
from tribal_assistant.core.agents.learning import LessonBook
from tribal_assistant.core.agents.proposers.attack import AttackProposer
from tribal_assistant.core.agents.proposers.farm import FarmPlanner
from tribal_assistant.core.agents.roles.operator import OperatorAgent
from tribal_assistant.core.agents.toolbox import Toolbox
from tribal_assistant.core.agents.tools.base import ToolOutcome
from tribal_assistant.core.agents.tools.farm import SetFarmTemplates
from tribal_assistant.core.game.result import ActionResult
from tribal_assistant.core.game.scraper.farm_assistant import FarmAssistantParser
from tribal_assistant.core.models.world import WorldVillage
from tribal_assistant.core.schemas.agent_settings import AgentSettings

FIXTURE = Path(__file__).parents[1] / "fixtures" / "html" / "farm_assistant.html"

BUTTONS = """<td><a href="#" onclick="return Accountmanager.farm.sendUnits(this, 102073, 5471)" class="farm_village_102073 farm_icon farm_icon_a"></a></td>
        <td><a href="#" onclick="return Accountmanager.farm.sendUnits(this, 102073, 5472)" class="farm_village_102073 farm_icon farm_icon_b farm_icon_disabled"></a></td>
        <td style="text-align: center">"""
RESOURCES = """<td style="text-align: center;" colspan="3"><span class="nowrap"><span class="icon header wood"></span>1.234</span> <span class="nowrap"><span class="icon header stone"></span>567</span> <span class="nowrap"><span class="icon header iron"></span>89</span></td>

        <td style="text-align: center;">1</td>"""


def real() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def with_templates() -> str:
    html = real().replace('name="light[0]" size="3" value="0"', 'name="light[0]" size="3" value="5"')
    html = html.replace('name="light[1]" size="3" value="0"', 'name="light[1]" size="3" value="15"')
    html = html.replace('<td style="text-align: center">\n                    <span', BUTTONS + '\n                    <span', 1)
    start = html.index('<td style="text-align: center;" colspan="3">')
    end = html.index('<td style="text-align: center;">?</td>', start) + len('<td style="text-align: center;">?</td>')
    return html[:start] + RESOURCES + html[end:]


def test_saved_template_takes_its_game_id_as_field_index():
    html = real().replace("[0]", "[3098]").replace('name="spear[3098]" size="3" value="0"', 'name="spear[3098]" size="3" value="16"')
    state = FarmAssistantParser.parse(html)

    assert state["templates"]["a"]["index"] == 3098 and state["templates"]["b"]["index"] == 1
    assert FarmAssistantParser.squad(state, "a") == {"spear": 16} and FarmAssistantParser.squad(state, "b") == {}


def test_real_screen_reads_templates_home_and_targets():
    state = FarmAssistantParser.parse(real())

    assert state["available"] and not state["premium_required"]
    assert state["templates"]["a"]["id"] == "0" and state["templates"]["a"]["new"]
    assert FarmAssistantParser.squad(state, "a") == {} and FarmAssistantParser.squad(state, "b") == {}
    assert set(state["templates"]["b"]["units"]) >= {"spear", "light", "knight"}
    assert state["home"]["spear"] == 5 and state["home"]["light"] == 0
    assert state["page_size"] == 15 and state["hide_attacked"]

    row = state["targets"][0]
    assert row["village_id"] == 102073 and row["coords"] == "490|749" and row["report_id"] == "64869872"
    assert row["result"] == "green" and row["full"] is True and row["time"] == "hoje às 01:40:35"
    assert row["resources"] is None and row["wall"] is None and row["distance"] == 9.4
    assert row["buttons"] == {"a": False, "b": False, "c": False}


def test_rows_with_buttons_resources_and_wall():
    state = FarmAssistantParser.parse(with_templates())
    row = state["targets"][0]

    assert FarmAssistantParser.squad(state, "a") == {"light": 5}
    assert FarmAssistantParser.squad(state, "b") == {"light": 15}
    assert row["buttons"] == {"a": True, "b": False, "c": False}
    assert row["template_ids"] == {"a": "5471", "b": "5472"}
    assert row["resources"] == {"wood": 1234, "clay": 567, "iron": 89}
    assert row["wall"] == 1
    assert FarmAssistantParser.target(state, "490|749") is row


def test_screen_without_the_assistant_is_unavailable():
    premium = FarmAssistantParser.parse('<td id="content_value"><a href="/game.php?screen=premium&mode=use">Ativar</a></td>')
    assert not premium["available"] and premium["premium_required"] and premium["targets"] == []

    assert not FarmAssistantParser.parse("")["available"]
    home = FarmAssistantParser.parse('<script>Accountmanager.farm.current_units = {"spear":"7","light":"2"};</script>')
    assert home["home"] == {"spear": 7, "light": 2}


def test_templates_follow_the_troops_and_the_wall_table():
    knobs = Knobs()

    assert FarmPlanner.templates({"light": 40}, [], knobs) == {"a": {"light": 5}, "b": {"light": 15}}
    assert FarmPlanner.templates({"light": 40}, [2], Knobs({"farm.template_b_carry": 400, "raid.wall_light_factor": 2.0})) == {"a": {"light": 5}, "b": {"light": 16}}
    assert FarmPlanner.templates({"spear": 30, "light": 3}, [], knobs) == {"a": {"spear": 16}, "b": {}}
    assert FarmPlanner.templates({"spear": 5}, [], knobs) == {"a": {}, "b": {}}
    assert FarmPlanner.templates({"light": 40}, [], Knobs({"farm.template_b_carry": 1600}))["b"] == {"light": 20}


def test_templates_are_saved_again_only_when_they_drift():
    knobs = Knobs()
    wanted = {"a": {"light": 5}, "b": {"light": 15}}

    assert not FarmPlanner.drifted(wanted, wanted, knobs)
    assert not FarmPlanner.drifted({"a": {"light": 5}, "b": {"light": 17}}, wanted, knobs)
    assert FarmPlanner.drifted({"a": {"light": 5}, "b": {"light": 25}}, wanted, knobs)
    assert FarmPlanner.drifted({"a": {}, "b": {}}, wanted, knobs)
    assert FarmPlanner.drifted({"a": {"spear": 5}, "b": {"light": 15}}, wanted, knobs)


def test_a_for_open_barbarians_b_for_full_hauls_and_walls():
    knobs = Knobs()
    templates = {"a": {"light": 5}, "b": {"light": 15}}
    home = {"light": 40}
    row = {"village_id": 9, "coords": "503|500", "distance": 3, "buttons": {"a": True, "b": True}}

    assert FarmPlanner.choose(row, {"wall": 0, "full_streak": 1}, templates, home, knobs).template == "a"
    assert FarmPlanner.choose(row, {"wall": 0, "full_streak": 2}, templates, home, knobs).template == "b"
    assert FarmPlanner.choose(row, {"wall": 2}, templates, home, knobs).template == "b"
    assert FarmPlanner.choose({**row, "wall": 1}, {}, templates, home, knobs).template == "b"
    assert FarmPlanner.choose(row, {"wall": 3}, templates, home, knobs) is None
    assert FarmPlanner.choose(row, {"wall": 2}, {"a": {"light": 5}, "b": {"light": 6}}, home, knobs) is None
    assert FarmPlanner.choose(row, {"wall": 2}, templates, home, Knobs({"raid.wall_light_factor": 2.0})) is None
    assert FarmPlanner.choose({**row, "buttons": {"a": False, "b": True}}, {"wall": 0}, templates, home, knobs) is None
    assert FarmPlanner.choose(row, {"wall": 0}, templates, {"light": 3}, knobs) is None
    assert FarmPlanner.choose({**row, "distance": 11}, {"wall": 0}, templates, home, knobs) is None
    assert FarmPlanner.choose(row, {"wall": 0, "full_streak": 5}, templates, home, Knobs({"farm.full_streak_b": 6})).template == "a"


def test_farm_knobs_tune_from_the_hauls_the_list_shows():
    full = {"insights": [{"key": "farm_hauls", "text": "assistente de saque: 9/10 relatórios com carga cheia"}]}
    empty = {"insights": [{"key": "farm_hauls", "text": "assistente de saque: 0/10 relatórios com carga cheia"}]}

    metrics = Tuner.measure([full] * 12)
    assert round(metrics.farm_full, 2) == 0.9 and round(metrics.farm_partial, 2) == 0.1
    changes = {name: value for name, value, _ in Tuner.plan(Knobs(), metrics)}
    assert changes["farm.template_b_carry"] > 1200 and changes["farm.template_a_carry"] > 400
    assert changes["farm.full_streak_b"] == 1

    changes = {name: value for name, value, _ in Tuner.plan(Knobs(), Tuner.measure([empty] * 12))}
    assert changes["farm.template_b_carry"] < 1200 and changes["farm.template_a_carry"] < 400

    assert Tuner.measure([{"insights": []}] * 12).farm_full == 0.0
    assert "farm.template_b_carry" not in {name for name, _, _ in Tuner.plan(Knobs(), Metrics(rounds=12))}


async def test_farm_list_feeds_the_target_without_repeating_reports(session: AsyncSession):
    book = LessonBook(session)
    row = {"village_id": 9, "coords": "503|500", "report_id": "77", "result": "green", "full": True, "wall": 1, "resources": {"wood": 100}}

    assert await book.farm_list([row]) == 1
    data = await book.target("503|500")
    assert data["last_result"] == "green" and data["wall"] == 1 and data["full_streak"] == 1
    assert data["farm_resources"] == {"wood": 100} and "attacks" not in data

    assert await book.farm_list([row]) == 0
    assert (await book.target("503|500"))["full_streak"] == 1

    await book.repo.observe("report:78", "report", "relatório", "", {})
    await book.repo.observe("target:503|500", "target", "alvo", "", {"last_result": "yellow", "attacks": 3, "wall": 0})
    await book.farm_list([{**row, "report_id": "78", "result": "green", "wall": 2}])
    data = await book.target("503|500")
    assert data["full_streak"] == 2 and data["last_result"] == "yellow" and data["attacks"] == 3 and data["wall"] == 0

    await book.farm_list([{**row, "report_id": "79", "full": False}])
    assert (await book.target("503|500"))["full_streak"] == 0


async def barbarians(session: AsyncSession) -> None:
    session.add_all(
        [
            WorldVillage(id=9, name="Bárbara", x=503, y=500, player_id=0, points=30),
            WorldVillage(id=10, name="Jogador", x=502, y=500, player_id=77, points=300),
            WorldVillage(id=12, name="Outra bárbara", x=504, y=500, player_id=0, points=30),
        ]
    )
    await session.commit()


async def test_template_raid_only_on_the_barbarian_of_the_row(session: AsyncSession):
    await barbarians(session)
    guard = Guardrails(session, AgentSettings())
    ctx = context(units=[unit("light", 20)])

    assert await guard.check_farm_template(ctx, "503|500", 9, {"light": 5}) is None
    assert "bárbara" in await guard.check_farm_template(ctx, "502|500", 10, {"light": 5})
    assert "não é bárbara" in await guard.check_farm_template(ctx, "503|500", 10, {"light": 5})
    assert "fica em" in await guard.check_farm_template(ctx, "503|500", 12, {"light": 5})
    assert "não é bárbara" in await guard.check_farm_template(ctx, "503|500", 11, {"light": 5})
    assert "só há" in await guard.check_farm_template(ctx, "503|500", 9, {"light": 50})
    assert "vazio" in await guard.check_farm_template(ctx, "503|500", 9, {})


class FakeFarm:
    def __init__(self, state: dict) -> None:
        self.state_value = state
        self.calls: list[tuple] = []

    async def state(self, village_id: str) -> dict:
        return self.state_value

    async def send(self, village_id: str, target_id: int, coords: str, letter: str, units: dict) -> ActionResult:
        self.calls.append(("send", target_id, coords, letter, units))
        return ActionResult(True, "send_farm_template", f"saque modelo {letter.upper()} enviado para {coords}")

    async def set_templates(self, village_id: str, wanted: dict) -> ActionResult:
        self.calls.append(("templates", wanted))
        return ActionResult(True, "set_farm_templates", "modelos salvos")


def box(session: AsyncSession, farm: FakeFarm, ctx=None) -> Toolbox:
    return Toolbox(
        agent=OperatorAgent(),
        ctx=ctx or context(units=[unit("light", 20)]),
        session=session,
        config=AgentSettings(),
        run_id="farm",
        dry_run=False,
        actions=SimpleNamespace(farm=farm),
    )


async def test_operator_tools_send_through_the_assistant_with_the_same_guardrails(session: AsyncSession):
    await barbarians(session)
    farm = FakeFarm(FarmAssistantParser.parse(with_templates()))
    toolbox = box(session, farm)

    read = await toolbox.invoke("read_farm_assistant", {})
    assert read.ok and json.loads(read.text)["templates"] == {"a": {"light": 5}, "b": {"light": 15}}

    sent = await toolbox.invoke("send_farm_template", {"target": "503|500", "target_id": 9, "template": "a", "reason": "teste"})
    assert sent.ok and farm.calls == [("send", 9, "503|500", "a", {"light": 5})]
    assert toolbox.ctx.unit("light").home == 15

    again = await toolbox.invoke("send_farm_template", {"target": "503|500", "target_id": 9, "template": "a", "reason": "teste"})
    assert not again.ok and "últimos" in again.text

    player = await toolbox.invoke("send_farm_template", {"target": "502|500", "target_id": 10, "template": "a", "reason": "teste"})
    assert not player.ok and "bárbara" in player.text and len(farm.calls) == 1

    saved = await toolbox.invoke("set_farm_templates", {"a": {"light": 6}, "b": {"light": 16}, "reason": "teste"})
    assert saved.ok and farm.calls[-1] == ("templates", {"a": {"light": 6}, "b": {"light": 16}})


def test_templates_refuse_nobles_and_unknown_units():
    assert "snob" in SetFarmTemplates.refusal({"a": {"snob": 1}})
    assert "dragão" in SetFarmTemplates.refusal({"a": {"dragão": 1}})
    assert SetFarmTemplates.refusal({}) is not None
    assert SetFarmTemplates.refusal({"a": {"light": 5}, "b": {}}) is None


async def test_unavailable_assistant_is_remembered(session: AsyncSession):
    farm = FakeFarm({"available": False, "reason": "pede conta premium", "targets": []})
    toolbox = box(session, farm)

    first = await toolbox.invoke("read_farm_assistant", {})
    assert first.ok and not first.data["available"] and "premium" in first.text

    farm.state_value = FarmAssistantParser.parse(with_templates())
    second = await toolbox.invoke("read_farm_assistant", {})
    assert not second.data["available"] and "visto há pouco" in second.text


def view(state: dict | None, light: int = 40, intel: dict | None = None) -> SimpleNamespace:
    listing = [{"coords": "490|749", "points": 30, "distance": 3, "recently_attacked": False}]
    ctx = context(units=[unit("light", light), unit("spy", 0)])
    notes: list = []

    async def read(tool: str, arguments: dict | None = None) -> ToolOutcome:
        if tool == "list_barbarians":
            return ToolOutcome(True, json.dumps(listing))
        if tool == "read_farm_assistant":
            return ToolOutcome(True, "", state or {"available": False})
        return ToolOutcome(False, "")

    async def target(coords: str) -> dict:
        return dict(intel or {"attacks": 2, "last_result": "green", "avg_haul": 300, "wall": 0})

    async def get(key: str) -> None:
        return None

    async def zero(*args) -> int:
        return 0

    async def no(*args) -> bool:
        return False

    return SimpleNamespace(
        ctx=ctx,
        knobs=Knobs(),
        role="growth",
        read=read,
        note=notes.append,
        notes=notes,
        lessons=SimpleNamespace(target=target, repo=SimpleNamespace(get=get)),
        guard=SimpleNamespace(attacks_last_hour=zero, spied_recently=no),
    )


async def test_without_the_assistant_raids_go_through_the_rally_point():
    items = await AttackProposer()._raids(view(None))

    assert [p.action for p in items] == ["send_farm_attack"]


async def test_with_templates_ready_the_raid_clicks_a():
    state = FarmAssistantParser.parse(with_templates().replace("farm_icon_b farm_icon_disabled", "farm_icon_b"))
    state["targets"][0]["wall"] = None
    fake = view(state)

    items = await AttackProposer()._raids(fake)

    assert [p.action for p in items] == ["send_farm_template"]
    assert items[0].arguments["template"] == "a" and items[0].arguments["target_id"] == 102073
    assert items[0].troops == {"light": 5}
    assert any(n.key == "farm_hauls" and "1/1" in n.text for n in fake.notes)

    items = await AttackProposer()._raids(view(state, intel={"attacks": 3, "last_result": "green", "avg_haul": 300, "wall": 0, "full_streak": 3}))
    assert items[0].arguments["template"] == "b" and items[0].troops == {"light": 15}


async def test_templates_that_drift_are_saved_and_the_round_uses_the_rally_point():
    items = await AttackProposer()._raids(view(FarmAssistantParser.parse(real())))

    assert [p.action for p in items] == ["set_farm_templates", "send_farm_attack"]
    assert items[0].arguments["a"] == {"light": 5} and items[0].arguments["b"] == {"light": 15}
