"""Village repository — DB access only, no domain logic."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.models.village import Village
from tribal_assistant.schemas.village import VillageCreate, VillageUpdate


class VillageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> Sequence[Village]:
        result = await self.session.execute(select(Village).order_by(Village.coords))
        return result.scalars().all()

    async def get(self, village_id: int) -> Village | None:
        return await self.session.get(Village, village_id)

    async def get_by_coords(self, coords: str) -> Village | None:
        result = await self.session.execute(select(Village).where(Village.coords == coords))
        return result.scalar_one_or_none()

    async def create(self, payload: VillageCreate) -> Village:
        village = Village(**payload.model_dump())
        self.session.add(village)
        await self.session.commit()
        await self.session.refresh(village)
        return village

    async def update(self, village: Village, patch: VillageUpdate) -> Village:
        for field, value in patch.model_dump(exclude_none=True).items():
            setattr(village, field, value)
        await self.session.commit()
        await self.session.refresh(village)
        return village

    async def upsert_by_coords(self, payload: VillageCreate) -> Village:
        existing = await self.get_by_coords(payload.coords)
        if existing is None:
            return await self.create(payload)
        for field, value in payload.model_dump(exclude={"coords"}).items():
            setattr(existing, field, value)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing
