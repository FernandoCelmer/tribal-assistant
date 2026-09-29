"""Data access for learned lessons."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.models.lesson import Lesson


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class LessonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> Lesson | None:
        return (await self.session.execute(select(Lesson).where(Lesson.key == key))).scalar_one_or_none()

    async def observe(
        self,
        key: str,
        topic: str,
        title: str,
        text: str = "",
        data: dict[str, Any] | None = None,
        ok: bool | None = None,
        commit: bool = True,
    ) -> Lesson:
        now = _now()
        row = await self.get(key)

        if row is None:
            row = Lesson(key=key, topic=topic, title=title[:255], first_seen=now, last_seen=now)
            self.session.add(row)

        row.title = title[:255]
        row.text = text or row.text
        row.seen = (row.seen or 0) + 1
        row.last_seen = now

        if data is not None:
            row.data = json.dumps({**json.loads(row.data or "{}"), **data}, ensure_ascii=False, default=str)

        if ok is True:
            row.ok = (row.ok or 0) + 1
        elif ok is False:
            row.failed = (row.failed or 0) + 1

        if commit:
            await self.session.commit()

        return row

    async def recent_failure(self, key: str, minutes: int, times: int) -> Lesson | None:
        row = await self.get(key)
        if row is None or row.failed < times:
            return None

        return row if _now() - row.last_seen <= timedelta(minutes=minutes) else None

    async def list(self, topic: str | None = None, limit: int = 100) -> Sequence[Lesson]:
        stmt = select(Lesson).order_by(Lesson.last_seen.desc()).limit(limit)
        if topic:
            stmt = stmt.where(Lesson.topic == topic)

        return (await self.session.execute(stmt)).scalars().all()
