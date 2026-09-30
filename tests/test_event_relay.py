import asyncio

from tribal_assistant.core.event_relay import MAX_BYTES, MAX_TEXT, EventRelay
from tribal_assistant.core.events import Event, EventBus


def test_encode_round_trips_and_shortens_long_texts():
    event = Event("flow", {"phase": "result", "text": "x" * 5_000, "items": [{"why": "y" * 2_000}]})
    payload = EventRelay.encode(event)

    assert payload is not None and len(payload.encode()) <= MAX_BYTES
    back = EventRelay.decode(payload)
    assert back.kind == "flow" and back.at == event.at
    assert len(back.data["text"]) == MAX_TEXT and len(back.data["items"][0]["why"]) == MAX_TEXT


def test_decode_ignores_garbage():
    assert EventRelay.decode("not json") is None
    assert EventRelay.decode('{"kind": "x"}') is None


def test_bus_relays_local_events_but_not_received_ones():
    async def scenario() -> tuple[list[str], list[str]]:
        bus = EventBus()
        bus.bind(asyncio.get_running_loop())
        relayed: list[str] = []
        bus.relay = lambda event: relayed.append(event.kind)
        queue = bus.subscribe()

        bus.publish("decision", {"action": "a"})
        bus.receive(Event("flow", {"phase": "start"}))
        await asyncio.sleep(0.01)

        seen = [queue.get_nowait().kind for _ in range(queue.qsize())]
        return seen, relayed

    seen, relayed = asyncio.run(scenario())
    assert seen == ["decision", "flow"]
    assert relayed == ["decision"]


def test_debug_logs_stay_local():
    relay = EventRelay(EventBus())
    relay.send(Event("log", {"level": "DEBUG", "message": "m"}))
    relay.send(Event("log", {"level": "INFO", "message": "m"}))
    relay.send(Event("flow", {"phase": "done"}))

    assert relay.queue.qsize() == 2
