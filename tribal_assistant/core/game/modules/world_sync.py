"""Refreshes the public world data tables."""

from loguru import logger

from tribal_assistant.core.db.session import SessionFactory
from tribal_assistant.core.game.world import fetch_world
from tribal_assistant.core.repositories.world import WorldRepository


async def sync_world() -> None:
    data = await fetch_world()
    async with SessionFactory() as session:
        await WorldRepository(session).replace(data)

        from tribal_assistant.core.agents.learning import LessonBook

        await LessonBook(session).neighbourhood()
    logger.info(
        "Mundo sincronizado: {} aldeias, {} jogadores, {} tribos",
        len(data.villages), len(data.players), len(data.allies),
    )
