"""Carries bus events between processes through Postgres NOTIFY: the server that plays sends, a read-only panel listens."""

import asyncio
import json
from typing import Any

import asyncpg
from loguru import logger

from tribal_assistant.core.config import settings
from tribal_assistant.core.events import Event, EventBus

CHANNEL = "tribal_events"
MAX_BYTES = 7_800
MAX_TEXT = 600
RETRY_SECONDS = 5
QUEUE_SIZE = 1_000
QUIET_LEVELS = frozenset({"TRACE", "DEBUG"})


class EventRelay:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=QUEUE_SIZE)
        self.task: asyncio.Task[None] | None = None

    @staticmethod
    def dsn() -> str | None:
        url = settings.database_url
        if not url.startswith("postgresql"):
            return None
        return "postgresql://" + url.split("://", 1)[1]

    @staticmethod
    def shrink(value: Any) -> Any:
        if isinstance(value, str):
            return value if len(value) <= MAX_TEXT else value[: MAX_TEXT - 1] + "…"
        if isinstance(value, dict):
            return {k: EventRelay.shrink(v) for k, v in value.items()}
        if isinstance(value, list):
            return [EventRelay.shrink(v) for v in value]
        return value

    @classmethod
    def encode(cls, event: Event) -> str | None:
        payload = json.dumps({"kind": event.kind, "at": event.at, "data": cls.shrink(event.data)}, ensure_ascii=False, default=str)
        return payload if len(payload.encode()) <= MAX_BYTES else None

    @staticmethod
    def decode(payload: str) -> Event | None:
        try:
            raw = json.loads(payload)
            return Event(str(raw["kind"]), dict(raw["data"]), str(raw["at"]))
        except (ValueError, KeyError, TypeError):
            return None

    def start(self) -> None:
        dsn = self.dsn()
        if dsn is None:
            return

        if settings.play:
            self.bus.relay = self.send
            self.task = asyncio.create_task(self._sender(dsn))
        else:
            self.task = asyncio.create_task(self._listener(dsn))

    async def stop(self) -> None:
        self.bus.relay = None
        if self.task is not None:
            self.task.cancel()
            self.task = None

    def send(self, event: Event) -> None:
        if event.kind == "log" and event.data.get("level") in QUIET_LEVELS:
            return
        if self.queue.full():
            self.queue.get_nowait()
        self.queue.put_nowait(event)

    async def _sender(self, dsn: str) -> None:
        while True:
            try:
                connection = await asyncpg.connect(dsn)
                try:
                    while True:
                        event = await self.queue.get()
                        payload = self.encode(event)
                        if payload is not None:
                            await connection.execute("SELECT pg_notify($1, $2)", CHANNEL, payload)
                finally:
                    await connection.close()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Ponte de eventos (envio) caiu: {}; tentando de novo", exc)
                await asyncio.sleep(RETRY_SECONDS)

    async def _listener(self, dsn: str) -> None:
        def received(_connection: Any, _pid: int, _channel: str, payload: str) -> None:
            event = self.decode(payload)
            if event is not None:
                self.bus.receive(event)

        while True:
            try:
                connection = await asyncpg.connect(dsn)
                try:
                    await connection.add_listener(CHANNEL, received)
                    logger.info("Ponte de eventos ouvindo o servidor que joga")
                    while not connection.is_closed():
                        await asyncio.sleep(RETRY_SECONDS)
                        await connection.execute("SELECT 1")
                finally:
                    await connection.close()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Ponte de eventos (escuta) caiu: {}; tentando de novo", exc)
                await asyncio.sleep(RETRY_SECONDS)
