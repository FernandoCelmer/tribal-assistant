"""Farm target repository."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.models.farm_target import FarmTarget
from tribal_assistant.schemas.farm import FarmTargetCreate


class FarmTargetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, enabled_only: bool = True) -> Sequence[FarmTarget]:
        stmt = select(FarmTarget).order_by(FarmTarget.last_attack_at.asc().nulls_first())
        if enabled_only:
            stmt = stmt.where(FarmTarget.enabled.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get(self, target_id: int) -> FarmTarget | None:
        return await self.session.get(FarmTarget, target_id)

    async def get_by_coords(self, coords: str) -> FarmTarget | None:
        result = await self.session.execute(select(FarmTarget).where(FarmTarget.coords == coords))
        return result.scalar_one_or_none()

    async def create(self, payload: FarmTargetCreate) -> FarmTarget:
        target = FarmTarget(**payload.model_dump())
        self.session.add(target)
        await self.session.commit()
        await self.session.refresh(target)
        return target

    async def delete(self, target: FarmTarget) -> None:
        await self.session.delete(target)
        await self.session.commit()

    async def mark_attacked(self, target: FarmTarget, loot: int) -> FarmTarget:
        target.last_attack_at = datetime.utcnow()
        target.last_loot = loot
        await self.session.commit()
        await self.session.refresh(target)
        return target
