"""Village service."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.repositories.villages import VillageRepository
from tribal_assistant.core.schemas.village import VillageCreate, VillageUpdate


class VillageService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = VillageRepository(session)

    async def list(self) -> Sequence[Village]:
        return await self.repository.list()

    async def get(self, village_id: int) -> Village:
        village = await self.repository.get(village_id)
        if village is None:
            raise NotFoundError(f"village {village_id} not found")
        return village

    async def upsert(self, payload: VillageCreate) -> Village:
        return await self.repository.upsert_by_coords(payload)

    async def update(self, village_id: int, patch: VillageUpdate) -> Village:
        village = await self.get(village_id)
        return await self.repository.update(village, patch)
