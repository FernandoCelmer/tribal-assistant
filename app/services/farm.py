"""Farm service."""

from collections.abc import Sequence

from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError
from app.db.session import get_session
from app.models.farm_target import FarmTarget
from app.repositories.farm import FarmTargetRepository
from app.schemas.farm import FarmTargetCreate, FarmTickResult


class FarmService:
    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        self.repository = FarmTargetRepository(session)

    async def list(self) -> Sequence[FarmTarget]:
        return await self.repository.list()

    async def add(self, payload: FarmTargetCreate) -> FarmTarget:
        if await self.repository.get_by_coords(payload.coords):
            raise ConflictError(f"farm target {payload.coords} already exists", field="coords")
        return await self.repository.create(payload)

    async def get(self, target_id: int) -> FarmTarget:
        target = await self.repository.get(target_id)
        if target is None:
            raise NotFoundError(f"farm target {target_id} not found")
        return target

    async def tick(self) -> FarmTickResult:
        """Send farm attacks against enabled targets.

        Actual browser dispatch happens in `app.bot.modules.farm`. This service
        orchestrates the DB round-trips.
        """
        if not settings.farm_enabled:
            logger.info("Farm disabled by config, skipping tick")
            return FarmTickResult(dispatched=0, skipped=0)

        from app.bot.modules.farm import FarmRunner  # local import breaks cycle

        targets = list(await self.repository.list(enabled_only=True))
        runner = FarmRunner()
        result = await runner.dispatch(targets)

        for coords, loot in result.persisted_loots.items():
            target = await self.repository.get_by_coords(coords)
            if target:
                await self.repository.mark_attacked(target, loot)

        return FarmTickResult(
            dispatched=result.dispatched,
            skipped=result.skipped,
            errors=result.errors,
        )
