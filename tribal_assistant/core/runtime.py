"""Starts and stops the engine: database, leftover runs, scheduler and browser sessions."""

import asyncio

from loguru import logger

from tribal_assistant.core.config import settings
from tribal_assistant.core.db.session import SessionFactory, init_db
from tribal_assistant.core.event_relay import EventRelay
from tribal_assistant.core.events import event_bus
from tribal_assistant.core.game.session import game_session
from tribal_assistant.core.logging import configure_logging
from tribal_assistant.core.repositories.observability import ObservabilityRepository
from tribal_assistant.core.scheduler.runtime import scheduler


class Engine:
    """Everything that plays the game in the background, independent of any interface."""

    def __init__(self) -> None:
        self.relay = EventRelay(event_bus)

    async def start(self, schedule: bool = True) -> None:
        configure_logging(settings.log_level)
        event_bus.bind(asyncio.get_running_loop())
        await init_db()

        if not schedule:
            return

        self.relay.start()

        if not settings.play:
            logger.warning("PLAY=false: este servidor só atende a API; agentes, sincronizações e navegador do jogo ficam desligados")
            return

        async with SessionFactory() as session:
            await ObservabilityRepository(session).interrupt_stale(older_than_minutes=0)

        scheduler.start()

    async def stop(self) -> None:
        await self.relay.stop()
        if scheduler.running:
            scheduler.shutdown(wait=False)

        await game_session.close()


engine = Engine()
