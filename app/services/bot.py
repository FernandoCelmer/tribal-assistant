"""Bot control service."""

from app.core.config import settings
from app.schemas.bot import BotCommandResult, BotStatus
from app.scheduler.runtime import scheduler


class BotService:
    async def status(self) -> BotStatus:
        jobs = [job.id for job in scheduler.get_jobs()]
        return BotStatus(
            running=scheduler.running,
            logged_in=False,  # populated by scraper on next sync
            world=settings.tw_server,
            scheduler_jobs=jobs,
        )

    async def start(self) -> BotCommandResult:
        if not scheduler.running:
            scheduler.start()
        return BotCommandResult(ok=True, message="scheduler started")

    async def stop(self) -> BotCommandResult:
        if scheduler.running:
            scheduler.pause()
        return BotCommandResult(ok=True, message="scheduler paused")
