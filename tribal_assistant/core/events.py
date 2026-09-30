"""In-process publish/subscribe for live dashboard updates (Server-Sent Events)."""

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from tribal_assistant.core.accounts.context import current_account_id


@dataclass
class Event:
    kind: str
    data: dict[str, Any]
    at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


class EventBus:
    """Fan-out to every subscriber queue; safe to publish from any thread."""

    def __init__(self, queue_size: int = 500) -> None:
        self.queue_size = queue_size
        self._subscribers: set[asyncio.Queue[Event]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=self.queue_size)

        with self._lock:
            self._subscribers.add(queue)

        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, kind: str, data: dict[str, Any]) -> None:
        data = {"account_id": current_account_id(), **data}
        event = Event(kind, data)
        loop = self._loop

        if loop is None or loop.is_closed():
            return

        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is loop:
            self._deliver(event)
        else:
            loop.call_soon_threadsafe(self._deliver, event)

    def _deliver(self, event: Event) -> None:
        with self._lock:
            subscribers = list(self._subscribers)

        for queue in subscribers:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)


event_bus = EventBus()
