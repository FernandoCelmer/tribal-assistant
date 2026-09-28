"""Scheduled jobs. Kept trivial: each job calls a service/module coroutine."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.core.config import settings


async def _sync_village_job() -> None:
    from app.bot.modules.village_sync import sync_current_village

    try:
        await sync_current_village()
    except Exception:  # noqa: BLE001
        logger.exception("village sync failed")


async def _farm_tick_job() -> None:
    from app.db.session import SessionFactory
    from app.services.farm import FarmService

    async with SessionFactory() as session:
        service = FarmService.__new__(FarmService)
        from app.repositories.farm import FarmTargetRepository

        service.repository = FarmTargetRepository(session)
        try:
            await service.tick()
        except Exception:  # noqa: BLE001
            logger.exception("farm tick failed")


def register_jobs(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        _sync_village_job,
        trigger=IntervalTrigger(minutes=5),
        id="sync_village",
        replace_existing=True,
    )
    if settings.farm_enabled:
        scheduler.add_job(
            _farm_tick_job,
            trigger=IntervalTrigger(minutes=5),
            id="farm_tick",
            replace_existing=True,
        )
