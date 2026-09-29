"""Assistant control service."""

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.accounts.context import current_world
from tribal_assistant.core.config import settings
from tribal_assistant.core.game.state import session_state
from tribal_assistant.core.scheduler.runtime import scheduler
from tribal_assistant.core.schemas.assistant import AssistantStatus, CommandResult


class AssistantService:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def status(self) -> AssistantStatus:
        from tribal_assistant.core.repositories.agent_settings import AgentSettingsRepository

        jobs = [job.id for job in scheduler.get_jobs()]
        enabled = (await AgentSettingsRepository(self.session).get()).enabled if self.session else False
        return AssistantStatus(
            running=scheduler.running,
            playing=settings.play,
            agents_enabled=enabled,
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
