"""One machine plays an account at a time: a lease in the database, renewed while the browser is in use."""

import json
import socket
from datetime import UTC, datetime, timedelta

from loguru import logger

from tribal_assistant.core.agents.knobs import KnobStore
from tribal_assistant.core.db.session import SessionFactory
from tribal_assistant.core.errors import ConflictError
from tribal_assistant.core.repositories.lessons import LessonRepository

KEY = "session:lease"
RENEW_SHARE = 1 / 3


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SessionLease:
    def __init__(self, owner: str | None = None) -> None:
        self.owner = owner or socket.gethostname()
        self.renewed: datetime | None = None
        self.minutes: float | None = None

    async def hold(self) -> None:
        """Take or renew the lease; refuse while another machine holds a fresh one."""
        if self.renewed and self.minutes and _now() - self.renewed < timedelta(minutes=self.minutes * RENEW_SHARE):
            return

        async with SessionFactory() as session:
            self.minutes = (await KnobStore(session).load()).get("session.lease_minutes")
            lessons = LessonRepository(session)
            row = await lessons.get(KEY)
            holder = json.loads(row.data or "{}").get("owner") if row else None
            if holder and holder != self.owner and _now() - row.last_seen < timedelta(minutes=self.minutes):
                raise ConflictError(f"outra máquina ({holder}) está jogando esta conta agora; esta espera a vez")

            if holder != self.owner:
                logger.info("Esta máquina ({}) assumiu o jogo da conta", self.owner)
            await lessons.observe(KEY, "session", "máquina que está jogando", self.owner, {"owner": self.owner})
            self.renewed = _now()

    async def release(self) -> None:
        if self.renewed is None:
            return

        async with SessionFactory() as session:
            lessons = LessonRepository(session)
            row = await lessons.get(KEY)
            if row and json.loads(row.data or "{}").get("owner") == self.owner:
                await session.delete(row)
                await session.commit()
        self.renewed = None
