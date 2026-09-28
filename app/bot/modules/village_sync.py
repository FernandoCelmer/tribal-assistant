"""Reads current village from browser and persists snapshot."""

from loguru import logger

from app.bot.browser import open_browser
from app.bot.login import login
from app.bot.scraper.village import VillageSnapshot, scrape_village
from app.db.session import SessionFactory
from app.repositories.villages import VillageRepository
from app.schemas.village import VillageCreate


async def sync_current_village() -> VillageSnapshot:
    async with open_browser() as (page, _ctx):
        await login(page)
        html = await page.content()

    snapshot = scrape_village(html)
    logger.info("Village snapshot: {}", snapshot)

    async with SessionFactory() as session:
        repository = VillageRepository(session)
        await repository.upsert_by_coords(
            VillageCreate(
                name=snapshot.name,
                coords=snapshot.coords,
                is_own=True,
                wood=snapshot.wood,
                clay=snapshot.clay,
                iron=snapshot.iron,
                storage=snapshot.storage,
                pop_current=snapshot.pop_current,
                pop_max=snapshot.pop_max,
            )
        )

    return snapshot
