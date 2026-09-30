"""The next smithy research of a village: what it is, what it costs, and when it is done."""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.repositories.lessons import LessonRepository

KEY = "research:next"


class ResearchNeed:
    def __init__(self, session: AsyncSession, game_id: str) -> None:
        self.lessons = LessonRepository(session)
        self.key = f"{KEY}:{game_id}"

    async def get(self) -> dict[str, Any]:
        row = await self.lessons.get(self.key)
        return json.loads(row.data or "{}") if row else {}

    async def row(self):
        return await self.lessons.get(self.key)

    async def save(self, unit: str | None, cost: dict[str, int]) -> None:
        await self.lessons.observe(self.key, "research", f"próxima pesquisa: {unit or 'nenhuma'}", "", {"unit": unit, "cost": cost})

    async def done(self, unit: str) -> None:
        await self.lessons.observe(self.key, "research", f"pesquisa de {unit} iniciada", "", {"unit": None, "cost": {}})
