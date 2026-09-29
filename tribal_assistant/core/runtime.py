"""Starts and stops the engine: database, leftover runs, scheduler and browser sessions."""

import asyncio

from loguru import logger

from tribal_assistant.core.config import settings
from tribal_assistant.core.db.lease import EngineLease
from tribal_assistant.core.db.session import SessionFactory, init_db
from tribal_assistant.core.db.session import engine as database
from tribal_assistant.core.events import event_bus
from tribal_assistant.core.game.session import game_session
from tribal_assistant.core.logging import configure_logging
from tribal_assistant.core.repositories.observability import ObservabilityRepository
from tribal_assistant.core.scheduler.runtime import scheduler


class Engine:
    """Everything that plays the game in the background, independent of any interface."""

    def __init__(self) -> None:
        self.lease = EngineLease(database)
        self.playing = False

    async def start(self, schedule: bool = True) -> None:
        configure_logging(settings.log_level)
        event_bus.bind(asyncio.get_running_loop())
        await init_db()

        if not schedule:
            return

        if not await self.lease.acquire():
            logger.warning("Another server already plays with this database; this one only serves the API")
            return

        self.playing = True
        async with SessionFactory() as session:
            await ObservabilityRepository(session).interrupt_stale(older_than_minutes=0)

        scheduler.start()

    async def stop(self) -> None:
        if scheduler.running:
            scheduler.shutdown(wait=False)

        await game_session.close()
        await self.lease.release()
        self.playing = False


engine = Engine()
