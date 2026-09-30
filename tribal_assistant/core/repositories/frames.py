"""Timelapse pictures: store them, list them without the image bytes and read one image back."""

import json
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from tribal_assistant.core.models.frame import VillageFrame
from tribal_assistant.core.models.village import Village


class LevelDiff:
    """Buildings that went up between two pictures."""

    @staticmethod
    def parse(raw: str | None) -> dict[str, int]:
        try:
            data = json.loads(raw or "{}")
        except ValueError:
            return {}
        return {str(k): int(v) for k, v in data.items()} if isinstance(data, dict) else {}

    @staticmethod
    def ups(before: dict[str, int], after: dict[str, int]) -> list[tuple[str, int, int]]:
        return [(name, before.get(name, 0), level) for name, level in after.items() if level > before.get(name, 0)]

    @classmethod
    def gained(cls, before: dict[str, int], after: dict[str, int]) -> int:
        return sum(to - start for _, start, to in cls.ups(before, after))


class FrameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def village_id(self, game_id: str) -> int | None:
        stmt = select(Village.id).where(Village.game_id == game_id)
        return (await self.session.execute(stmt)).scalars().first()

    async def latest(self, village_id: int) -> VillageFrame | None:
        stmt = (
            select(VillageFrame)
            .where(VillageFrame.village_id == village_id)
            .options(defer(VillageFrame.image))
            .order_by(VillageFrame.taken_at.desc(), VillageFrame.id.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def listing(self, village_id: int) -> Sequence[VillageFrame]:
        stmt = (
            select(VillageFrame)
            .where(VillageFrame.village_id == village_id)
            .options(defer(VillageFrame.image))
            .order_by(VillageFrame.taken_at, VillageFrame.id)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def since(self, moment: datetime) -> Sequence[VillageFrame]:
        stmt = (
            select(VillageFrame)
            .where(VillageFrame.taken_at >= moment)
            .options(defer(VillageFrame.image))
            .order_by(VillageFrame.village_id, VillageFrame.taken_at, VillageFrame.id)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def image(self, frame_id: int) -> bytes | None:
        stmt = select(VillageFrame.image).where(VillageFrame.id == frame_id)
        return (await self.session.execute(stmt)).scalars().first()

    async def most_levels_gained(self, moment: datetime) -> int:
        """Largest number of building levels one village gained across the pictures since a moment."""
        best: dict[int, int] = {}
        previous: dict[int, dict[str, int]] = {}
        for frame in await self.since(moment):
            levels = LevelDiff.parse(frame.levels)
            before = previous.get(frame.village_id)
            if before is not None:
                best[frame.village_id] = best.get(frame.village_id, 0) + LevelDiff.gained(before, levels)
            previous[frame.village_id] = levels
        return max(best.values(), default=0)

    def add(self, frame: VillageFrame) -> None:
        self.session.add(frame)
