"""Scheduled jobs. Kept trivial: each job calls a service/module coroutine."""

from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from tribal_assistant.core.config import settings


async def _sync_game_job() -> None:
    from tribal_assistant.client.human import in_quiet_hours
    from tribal_assistant.client.modules.game_sync import sync_game

    if in_quiet_hours():
        logger.info("Quiet hours, skipping game sync")
        return
    try:
        await sync_game()
    except Exception:  # noqa: BLE001
        logger.exception("game sync failed")


async def _sync_world_job() -> None:
    from tribal_assistant.client.modules.world_sync import sync_world

    try:
        await sync_world()
    except Exception:  # noqa: BLE001
        logger.exception("world sync failed")


async def _farm_tick_job() -> None:
    from tribal_assistant.db.session import SessionFactory
    from tribal_assistant.services.farm import FarmService

    async with SessionFactory() as session:
        service = FarmService.__new__(FarmService)
        from tribal_assistant.repositories.farm import FarmTargetRepository

        service.repository = FarmTargetRepository(session)
        try:
            await service.tick()
        except Exception:  # noqa: BLE001
            logger.exception("farm tick failed")


def register_jobs(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        _sync_game_job,
        trigger=IntervalTrigger(
            seconds=settings.sync_interval_seconds,
            jitter=max(20, settings.sync_interval_seconds // 4),
        ),
        id="sync_game",
        next_run_time=datetime.now() + timedelta(seconds=10),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_world_job,
        trigger=IntervalTrigger(minutes=settings.world_sync_interval_minutes, jitter=120),
        id="sync_world",
        next_run_time=datetime.now() + timedelta(seconds=30),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    if settings.farm_enabled:
        scheduler.add_job(
            _farm_tick_job,
            trigger=IntervalTrigger(minutes=5),
            id="farm_tick",
            replace_existing=True,
        )
