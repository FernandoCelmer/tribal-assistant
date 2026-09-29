"""Watches the build queue and uses the free "finish now" button while its short window is open."""

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import select

from tribal_assistant.core.db.session import SessionFactory
from tribal_assistant.core.game.actions import GameActions
from tribal_assistant.core.models.building import Building
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.repositories.agent_settings import AgentSettingsRepository

WINDOW = timedelta(minutes=4)


class FreeFinishWatcher:
    def __init__(self, actions: GameActions | None = None) -> None:
        self.actions = actions or GameActions()

    async def due(self) -> list[str]:
        now = datetime.now(UTC).replace(tzinfo=None)

        async with SessionFactory() as session:
            config = await AgentSettingsRepository(session).get()
            if not config.auto_finish_free:
                return []

            rows = await session.execute(
                select(Village.game_id)
                .join(Building, Building.village_id == Village.id)
                .where(Building.queued_until.is_not(None))
                .where(Building.queued_until > now)
                .where(Building.queued_until <= now + WINDOW)
                .distinct()
            )

        return [game_id for game_id in rows.scalars() if game_id]

    async def run(self) -> int:
        finished = 0

        for game_id in await self.due():
            result = await self.actions.finish_free(game_id)
            if result.ok:
                finished += result.data.get("finished", 0)
                logger.info("Conclusão grátis na aldeia {}: {}", game_id, result.detail)

        return finished
