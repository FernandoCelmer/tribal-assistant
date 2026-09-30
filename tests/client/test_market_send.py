from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from tribal_assistant.core.game.conquest import ConfirmParser
from tribal_assistant.core.game.market import Market, SendParser

HTML = Path(__file__).resolve().parents[1] / "fixtures" / "html"
SEND = (HTML / "market_send.html").read_text(encoding="utf-8")
CONFIRM = """<td id="content_value"><form action="/game.php?village=105765&amp;screen=market&amp;mode=send&amp;action=send" method="post">
<table class="vis"><tr><td>Destino:</td><td><a href="#">Segunda aldeia (501|500) K75</a></td></tr>
<tr><td>Jogador:</td><td><a href="#">Player</a></td></tr><tr><td>Duração:</td><td>0:12:00</td></tr></table>
<input type="submit" class="btn" value="OK"></form></td>"""
DONE = '<td id="content_value"><p>Recursos enviados</p></td>'


def test_send_screen_reads_merchants_load_and_stock() -> None:
    form = SendParser.form(SEND)

    assert form == {
        "ready": True,
        "free": 4,
        "total": 5,
        "carry": 1000,
        "max_transport": 4000,
        "stock": {"wood": 155, "stone": 481, "iron": 525},
    }
    assert not SendParser.form("<p>sem mercado</p>")["ready"]


@pytest.mark.parametrize(
    "selector",
    [
        '#market-send-form input[name="wood"]',
        '#market-send-form input[name="stone"]',
        '#market-send-form input[name="iron"]',
        '#market-send-form input[name="target_type"][value="coord"]',
        "#market-send-form input.target-input-field",
        '#market-send-form input[type="submit"]',
        "#inputx",
        "#inputy",
    ],
)
def test_send_form_selectors_match_the_real_screen(selector: str) -> None:
    assert BeautifulSoup(SEND, "lxml").select_one(selector) is not None


def test_send_confirmation_shows_target_and_owner() -> None:
    assert SendParser.confirmation(CONFIRM) == {"coords": ["501|500"], "player": "Player"}


def test_rally_point_confirmation_tells_a_barbarian_from_a_player() -> None:
    html = (HTML / "place_confirm.html").read_text(encoding="utf-8")

    assert ConfirmParser.target(html) == {"player": "0", "coords": "474|751", "train": True}
    assert ConfirmParser.barbarian(html, "474|751") is None
    assert "esperado" in ConfirmParser.barbarian(html, "475|751")
    assert "dono" in ConfirmParser.barbarian(html.replace('data-player="0"', 'data-player="777"'), "474|751")


class FakeLocator:
    def __init__(self, page: "FakePage", selector: str) -> None:
        self.page = page
        self.selector = selector

    @property
    def first(self) -> "FakeLocator":
        return self

    def locator(self, selector: str) -> "FakeLocator":
        return FakeLocator(self.page, f"{self.selector} {selector}")

    async def count(self) -> int:
        return len(BeautifulSoup(self.page.html, "lxml").select(self.selector))

    async def fill(self, value: str) -> None:
        self.page.log.append(("fill", self.selector, value))

    async def check(self) -> None:
        self.page.log.append(("check", self.selector))

    async def click(self) -> None:
        self.page.log.append(("click", self.selector))

    async def type(self, value: str, delay: int = 0) -> None:
        self.page.log.append(("type", self.selector, value))


class FakePage:
    def __init__(self, html: str) -> None:
        self.html = html
        self.log: list[tuple] = []

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    async def content(self) -> str:
        return self.html

    async def evaluate(self, script: str, arg: object = None) -> None:
        self.log.append(("evaluate", arg))


class FakeActions:
    def __init__(self, confirm: str) -> None:
        self.page = FakePage(SEND)
        self.confirm = confirm

    async def _in_game(self, village_id: str, screen: str, **params: str) -> FakePage:
        self.page.log.append(("open", screen, params.get("mode")))
        return self.page

    async def _click_and_settle(self, page: FakePage, locator: FakeLocator) -> None:
        page.log.append(("submit", locator.selector))
        page.html = self.confirm if "market-send-form" in locator.selector else DONE

    def _capture(self, html: str, name: str) -> None:
        return None

    async def screen_messages(self, page: FakePage) -> dict[str, list[str]]:
        return {"errors": [], "notices": []}


async def test_send_fills_the_form_checks_the_confirmation_and_confirms(monkeypatch) -> None:
    monkeypatch.setattr("tribal_assistant.core.game.market.human_delay", _instant)
    actions = FakeActions(CONFIRM)

    result = await Market(actions).send_resources("105765", 501, 500, {"wood": 100, "clay": 200, "iron": 0}, owner="Player")

    assert result.ok, result.detail
    log = actions.page.log
    assert ("fill", '#market-send-form input[name="wood"]', "100") in log
    assert ("fill", '#market-send-form input[name="stone"]', "200") in log
    assert not any(e[0] == "fill" and "iron" in e[1] for e in log)
    assert ("type", "#market-send-form input.target-input-field", "501|500") in log
    assert log[-1][0] == "submit" and "action=send" in log[-1][1]


async def test_send_aborts_when_the_confirmation_shows_someone_else(monkeypatch) -> None:
    monkeypatch.setattr("tribal_assistant.core.game.market.human_delay", _instant)

    stranger = await Market(FakeActions(CONFIRM.replace(">Player<", ">Outro<"))).send_resources("105765", 501, 500, {"wood": 100}, owner="Player")
    elsewhere = await Market(FakeActions(CONFIRM)).send_resources("105765", 502, 500, {"wood": 100}, owner="Player")
    too_much = await Market(FakeActions(CONFIRM)).send_resources("105765", 501, 500, {"wood": 5000}, owner="Player")

    assert not stranger.ok and "Outro" in stranger.detail
    assert not elsewhere.ok and "502|500" in elsewhere.detail
    assert not too_much.ok and "comerciantes" in too_much.detail


async def _instant(*args: object) -> None:
    return None
