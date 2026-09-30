"""Village timelapse: decides when a sync picture is kept and serves the pictures back in order."""

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.core.game.camera import Shot, VillageCamera
from tribal_assistant.core.game.labels import label
from tribal_assistant.core.game.scraper.game import GameVillage
from tribal_assistant.core.models.frame import VillageFrame
from tribal_assistant.core.repositories.frames import FrameRepository, LevelDiff
from tribal_assistant.core.schemas.timelapse import FrameOut, LevelChange


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class FramePolicy:
    """A picture is kept on the first sync, after any building level up, or once the interval has passed."""

    def __init__(self, knobs: Knobs) -> None:
        self.interval = timedelta(hours=max(knobs.get("timelapse.interval_hours"), knobs.get("timelapse.min_interval_hours")))

    def due(self, last: VillageFrame | None, levels: dict[str, int], now: datetime) -> bool:
        if last is None:
            return True
        if LevelDiff.ups(LevelDiff.parse(last.levels), levels):
            return True
        return now - last.taken_at >= self.interval


class TimelapseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = FrameRepository(session)

    @staticmethod
    def camera(knobs: Knobs) -> VillageCamera:
        return VillageCamera(quality=knobs.int("timelapse.quality"), max_bytes=knobs.int("timelapse.max_kb") * 1024)

    async def record(self, villages: Sequence[GameVillage], shots: Mapping[str, Shot], knobs: Knobs) -> int:
        policy = FramePolicy(knobs)
        now = _now()
        kept = 0
        for village in villages:
            shot = shots.get(str(village.game_id))
            village_id = await self.repository.village_id(str(village.game_id)) if shot else None
            if shot is None or village_id is None:
                continue

            levels = {b.name: b.level for b in village.buildings}
            if not policy.due(await self.repository.latest(village_id), levels, now):
                continue

            self.repository.add(
                VillageFrame(
                    village_id=village_id,
                    taken_at=now,
                    image=shot.image,
                    width=shot.width,
                    height=shot.height,
                    points=village.points,
                    levels=json.dumps(levels, sort_keys=True),
                )
            )
            kept += 1

        if kept:
            await self.session.commit()
        return kept

    async def frames(self, village_id: int) -> list[FrameOut]:
        items = []
        before: dict[str, int] | None = None
        points: int | None = None
        for frame in await self.repository.listing(village_id):
            levels = LevelDiff.parse(frame.levels)
            ups = LevelDiff.ups(before, levels) if before is not None else []
            items.append(
                FrameOut(
                    id=frame.id,
                    taken_at=frame.taken_at.replace(tzinfo=UTC),
                    width=frame.width,
                    height=frame.height,
                    points=frame.points,
                    points_gained=frame.points - points if points is not None else 0,
                    levels=levels,
                    diff=[LevelChange(name=name, label=label(name), before=start, after=end) for name, start, end in ups],
                )
            )
            before, points = levels, frame.points
        return items

    async def image(self, frame_id: int) -> bytes:
        image = await self.repository.image(frame_id)
        if image is None:
            raise NotFoundError(f"foto {frame_id} não encontrada")
        return image
