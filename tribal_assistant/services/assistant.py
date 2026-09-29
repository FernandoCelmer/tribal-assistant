"""Assistant control service."""

from tribal_assistant.client.state import session_state
from tribal_assistant.core.config import settings
from tribal_assistant.scheduler.runtime import scheduler
from tribal_assistant.schemas.assistant import AssistantStatus, CommandResult


class AssistantService:
    async def status(self) -> AssistantStatus:
        jobs = [job.id for job in scheduler.get_jobs()]
        return AssistantStatus(
            running=scheduler.running,
            logged_in=session_state.logged_in,
            world=settings.tw_server,
            scheduler_jobs=jobs,
            last_sync_at=session_state.last_sync_at,
            last_error=session_state.last_error,
        )

    async def start(self) -> CommandResult:
        if not scheduler.running:
            scheduler.start()
        return CommandResult(ok=True, message="scheduler started")

    async def stop(self) -> CommandResult:
        if scheduler.running:
            scheduler.pause()
        return CommandResult(ok=True, message="scheduler paused")

    async def sync(self) -> CommandResult:
        from tribal_assistant.client.modules.game_sync import sync_game

        try:
            snapshot = await sync_game()
        except Exception as exc:
            return CommandResult(ok=False, message=str(exc))
        return CommandResult(
            ok=True, message=f"sincronizado: {len(snapshot.villages)} aldeia(s)"
        )
