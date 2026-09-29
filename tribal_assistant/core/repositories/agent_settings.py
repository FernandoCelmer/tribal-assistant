"""The single agent-settings row: read with defaults, patch, and track the last scheduled run."""

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.models.agent import AgentSettingsRow
from tribal_assistant.core.schemas.agent_settings import AgentSettings, AgentSettingsUpdate


class AgentSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _row(self) -> AgentSettingsRow:
        row = (await self.session.execute(select(AgentSettingsRow).limit(1))).scalar_one_or_none()

        if row is None:
            row = AgentSettingsRow(data=AgentSettings().model_dump_json())
            self.session.add(row)
            await self.session.commit()

        return row

    async def get(self) -> AgentSettings:
        row = await self._row()
        return AgentSettings.model_validate({**AgentSettings().model_dump(), **json.loads(row.data)})

    async def update(self, patch: AgentSettingsUpdate) -> AgentSettings:
        current = await self.get()
        merged = AgentSettings.model_validate({**current.model_dump(), **patch.model_dump(exclude_none=True)})

        row = await self._row()
        row.data = merged.model_dump_json()
        await self.session.commit()

        return merged

    async def last_run_at(self) -> datetime | None:
        return (await self._row()).last_run_at

    async def mark_run(self) -> None:
        row = await self._row()
        row.last_run_at = datetime.now(UTC).replace(tzinfo=None)
        await self.session.commit()
