"""Refreshes the public world data tables."""

from loguru import logger

from app.client.world import fetch_world
from app.db.session import SessionFactory
from app.repositories.world import WorldRepository


async def sync_world() -> None:
    data = await fetch_world()
    async with SessionFactory() as session:
        await WorldRepository(session).replace(data)
    logger.info(
        "World synced: {} villages, {} players, {} allies",
        len(data.villages), len(data.players), len(data.allies),
    )
