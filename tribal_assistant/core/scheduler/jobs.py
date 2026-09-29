"""Scheduled jobs. Kept trivial: each job calls a service/module coroutine."""

from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from tribal_assistant.core.agents.coordination.policy import BUILD_SLOTS
from tribal_assistant.core.config import settings


async def _accounts(one_per_world: bool = False) -> list:
    from tribal_assistant.core.accounts.registry import AccountRegistry
    from tribal_assistant.core.db.session import SessionFactory

    async with SessionFactory() as session:
        accounts = await AccountRegistry(session).contexts(enabled_only=True)

    if one_per_world:
        seen: dict[str, object] = {}
        for account in accounts:
            seen.setdefault(account.server, account)
        return list(seen.values())

    return accounts


def per_account(job, one_per_world: bool = False):
    """Runs `job` once for every enabled account, each inside its own account context."""
    from tribal_assistant.core.accounts.context import use_account

    async def run() -> None:
        for account in await _accounts(one_per_world):
            with use_account(account):
                try:
                    await job()
                except Exception:
                    logger.exception("{} falhou para a conta {}", job.__name__, account.name)

    run.__name__ = job.__name__
    return run


async def _sync_game_job() -> None:
    from tribal_assistant.core.game.human import in_quiet_hours
    from tribal_assistant.core.game.modules.game_sync import sync_game

    if in_quiet_hours():
        logger.info("Horário de silêncio, sincronização do jogo ignorada")
        return
    try:
        await sync_game()
    except Exception:
        logger.exception("falha na sincronização do jogo")


async def _sync_world_job() -> None:
    from tribal_assistant.core.game.modules.world_sync import sync_world

    try:
        await sync_world()
    except Exception:
        logger.exception("falha na sincronização do mundo")


async def _docs_job() -> None:
    from tribal_assistant.core.db.session import SessionFactory
    from tribal_assistant.core.services.docs import DocsService

    try:
        async with SessionFactory() as session:
            report = await DocsService(session).sync()
    except Exception:
        logger.exception("falha na sincronização dos docs")
        return

    if report.updated or report.removed:
        logger.info("Docs sincronizados: {} arquivo(s) atualizados, {} removidos, {} seções", report.updated, report.removed, report.chunks)


async def _tuning_job() -> None:
    from tribal_assistant.core.agents.knobs import Tuner
    from tribal_assistant.core.db.session import SessionFactory

    async with SessionFactory() as session:
        changes = await Tuner(session).run()

    for name, value, why in changes:
        logger.info("Ajuste automático: {} = {} ({})", name, value, why)


async def _build_slot_free(session, now: datetime, slots: int) -> bool:
    from sqlalchemy import func, select

    from tribal_assistant.core.models.building import Building
    from tribal_assistant.core.models.village import Village

    rows = await session.execute(
        select(Village.id, func.count(Building.id))
        .outerjoin(
            Building,
            (Building.village_id == Village.id)
            & Building.target_level.is_not(None)
            & (Building.queued_until.is_(None) | (Building.queued_until > now)),
        )
        .where(Village.is_own.is_(True))
        .group_by(Village.id)
    )
    return any(queued < slots for _, queued in rows.all())


async def _agents_job() -> None:
    from datetime import UTC

    from tribal_assistant.core.agents.runner import AgentRunner
    from tribal_assistant.core.db.session import SessionFactory
    from tribal_assistant.core.game.human import in_quiet_hours
    from tribal_assistant.core.repositories.agent_settings import AgentSettingsRepository

    async with SessionFactory() as session:
        repo = AgentSettingsRepository(session)
        config = await repo.get()
        last = await repo.last_run_at()

        if not config.enabled or in_quiet_hours():
            return

        now = datetime.now(UTC).replace(tzinfo=None)
        waited = now - last if last else None
        slot_free = await _build_slot_free(session, now, BUILD_SLOTS)
        early = slot_free and (waited is None or waited >= timedelta(seconds=90))

        if waited is not None and waited < timedelta(minutes=config.interval_minutes) and not early:
            return

        await repo.mark_run()

    try:
        report = await AgentRunner(trigger="schedule").run()
    except Exception:
        logger.exception("falha nos agentes das aldeias")
        return

    logger.info("Rodada dos agentes {} ({}): {}", report.run_id, report.brain, report.error or "ok")


async def _free_finish_job() -> None:
    from tribal_assistant.core.game.human import in_quiet_hours
    from tribal_assistant.core.game.modules.free_finish import FreeFinishWatcher

    if in_quiet_hours():
        return

    try:
        await FreeFinishWatcher().run()
    except Exception:
        logger.exception("falha no monitor de conclusão grátis")


async def _retention_job() -> None:
    from tribal_assistant.core.db.session import SessionFactory
    from tribal_assistant.core.repositories.observability import ObservabilityRepository

    async with SessionFactory() as session:
        removed = await ObservabilityRepository(session).prune(settings.trace_retention_days)

        from tribal_assistant.core.repositories.coordination import CoordinationRepository

        removed += await CoordinationRepository(session).prune(settings.trace_retention_days)

    logger.info("Retenção removeu {} linha(s) antigas de rastreio dos agentes", removed)


def register_jobs(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        per_account(_sync_game_job),
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
        per_account(_tuning_job),
        trigger=IntervalTrigger(hours=1, jitter=120),
        id="tuning",
        next_run_time=datetime.now() + timedelta(minutes=5),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        _docs_job,
        trigger=IntervalTrigger(hours=6, jitter=300),
        id="sync_docs",
        next_run_time=datetime.now() + timedelta(seconds=60),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        per_account(_sync_world_job, one_per_world=True),
        trigger=IntervalTrigger(minutes=settings.world_sync_interval_minutes, jitter=120),
        id="sync_world",
        next_run_time=datetime.now() + timedelta(seconds=30),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        per_account(_agents_job),
        trigger=IntervalTrigger(minutes=1, jitter=20),
        id="village_agents",
        next_run_time=datetime.now() + timedelta(seconds=90),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        per_account(_free_finish_job),
        trigger=IntervalTrigger(minutes=1, jitter=10),
        id="free_finish",
        next_run_time=datetime.now() + timedelta(seconds=60),
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
