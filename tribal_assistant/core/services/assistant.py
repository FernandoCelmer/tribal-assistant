"""Assistant control service."""

from tribal_assistant.core.accounts.context import current_world
from tribal_assistant.core.game.state import session_state
from tribal_assistant.core.scheduler.runtime import scheduler
from tribal_assistant.core.schemas.assistant import AssistantStatus, CommandResult


class AssistantService:
    async def status(self) -> AssistantStatus:
        jobs = [job.id for job in scheduler.get_jobs()]
        return AssistantStatus(
            running=scheduler.running,
            logged_in=session_state.logged_in,
            world=current_world() or "-",
            scheduler_jobs=jobs,
            last_sync_at=session_state.last_sync_at,
            last_error=session_state.last_error,
        )

    async def sync(self) -> CommandResult:
        from tribal_assistant.core.game.modules.game_sync import sync_game

        try:
            snapshot = await sync_game()
        except Exception as exc:
            return CommandResult(ok=False, message=str(exc))
        return CommandResult(
            ok=True, message=f"sincronizado: {len(snapshot.villages)} aldeia(s)"
        )
