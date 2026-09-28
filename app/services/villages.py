"""Village service."""

from collections.abc import Sequence

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.session import get_session
from app.models.village import Village
from app.repositories.villages import VillageRepository
from app.schemas.village import VillageCreate, VillageUpdate


class VillageService:
    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
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
