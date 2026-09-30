import asyncio
from unittest.mock import patch

from tribal_assistant.core.events import EventBus
from tribal_assistant.core.game.narrator import MAX_ARGS, Narrator


def test_arguments_drop_reason_and_empty_values():
    text = Narrator.arguments({"building": "farm", "reason": "porque sim", "note": "", "units": {"spear": 5}})

    assert text == 'building=farm, units={"spear": 5}'


def test_arguments_are_shortened():
    assert len(Narrator.arguments({"text": "x" * 1_000})) == MAX_ARGS


def test_query_reads_game_urls_only():
    assert Narrator.query("https://br144.tribalwars.com.br/game.php?village=1&screen=am_farm&mode=farm") == {"village": "1", "screen": "am_farm", "mode": "farm"}
    assert Narrator.query("https://www.tribalwars.com.br/page/login") is None


def test_place_names_screens_and_modes():
    assert Narrator.place("am_farm", {}) == "assistente de saque"
    assert Narrator.place("market", {"mode": "own_offer"}) == "mercado (own offer)"


class FieldStub:
    def __init__(self, kind: str, name: str) -> None:
        self.field = {"type": kind, "name": name}

    async def evaluate(self, _script: str, timeout: int = 0) -> dict:
        return self.field


def typed(target: FieldStub, text: str) -> list[dict]:
    async def scenario() -> list[dict]:
        bus = EventBus()
        bus.bind(asyncio.get_running_loop())
        queue = bus.subscribe()
        with patch("tribal_assistant.core.game.narrator.event_bus", bus):
            await Narrator.typing(target, text)
        await asyncio.sleep(0.01)
        return [queue.get_nowait().data for _ in range(queue.qsize())]

    return asyncio.run(scenario())


def test_typing_shows_the_field_and_the_text():
    [event] = typed(FieldStub("text", "res_sell_amount"), "300")

    assert event["step"] == "type" and event["field"] == "res_sell_amount" and event["text"] == "300"


def test_typing_never_shows_a_password():
    [event] = typed(FieldStub("password", "password"), "segredo")

    assert event["text"] == "••••"


def test_typing_survives_a_field_it_cannot_read():
    assert typed(object(), "x")[0]["field"] == "campo"
