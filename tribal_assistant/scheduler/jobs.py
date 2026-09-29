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
    except Exception:
        logger.exception("game sync failed")


async def _sync_world_job() -> None:
    from tribal_assistant.client.modules.world_sync import sync_world

    try:
        await sync_world()
    except Exception:
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
        except Exception:
            logger.exception("farm tick failed")


async def _agents_job() -> None:
    from datetime import UTC

    from tribal_assistant.agents.runner import AgentRunner
    from tribal_assistant.client.human import in_quiet_hours
    from tribal_assistant.db.session import SessionFactory
    from tribal_assistant.repositories.agent_settings import AgentSettingsRepository

    async with SessionFactory() as session:
        repo = AgentSettingsRepository(session)
        config = await repo.get()
        last = await repo.last_run_at()

        if not config.enabled or in_quiet_hours():
            return

        now = datetime.now(UTC).replace(tzinfo=None)
        if last and now - last < timedelta(minutes=config.interval_minutes):
            return

        await repo.mark_run()

    try:
        report = await AgentRunner(trigger="schedule").run()
    except Exception:
        logger.exception("village agents failed")
        return

    logger.info("Village agents run {} ({}): {}", report.run_id, report.brain, report.error or "ok")


async def _retention_job() -> None:
    from tribal_assistant.db.session import SessionFactory
    from tribal_assistant.repositories.observability import ObservabilityRepository

    async with SessionFactory() as session:
        removed = await ObservabilityRepository(session).prune(settings.trace_retention_days)

    logger.info("Retention removed {} old agent trace rows", removed)


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

    scheduler.add_job(
        _agents_job,
        trigger=IntervalTrigger(minutes=1, jitter=20),
        id="village_agents",
        next_run_time=datetime.now() + timedelta(seconds=90),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        _retention_job,
        trigger=IntervalTrigger(hours=24, jitter=600),
        id="trace_retention",
        next_run_time=datetime.now() + timedelta(minutes=5),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
