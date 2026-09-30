"""Watches the last rounds for a village that stopped moving and unlocks it: a reservation holding everything is suspended for a while."""

import json
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knobs import KnobStore
from tribal_assistant.core.repositories.coordination import CoordinationRepository
from tribal_assistant.core.repositories.lessons import LessonRepository

HELD = re.compile(r"reservados para ([^;]+)")
IDLE_QUEUE = "fila de obras: 0 ordem"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def suppression_key(purpose: str, village_id: int) -> str:
    return f"suppress:{purpose.strip()}:{village_id}"


class Watchdog:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.lessons = LessonRepository(session)

    @staticmethod
    def blocker(rounds: list[dict[str, Any]], least: int) -> str | None:
        """The reservation that held the whole stock with the build queue idle in enough of the last rounds."""
        stuck = 0
        purposes: Counter[str] = Counter()
        for data in rounds:
            budget = data.get("budget") or {}
            free = budget.get("free") or {}
            texts = " | ".join(str(i.get("text", "")) for i in data.get("insights") or [])
            if budget.get("stock") and all(free.get(r, 0) <= 0 for r in ("wood", "clay", "iron")) and IDLE_QUEUE in texts:
                stuck += 1
            for entry in data.get("deferred") or []:
                found = HELD.search(str(entry.get("why") or ""))
                if found:
                    purposes.update(p.strip() for p in found.group(1).split(","))
        if stuck < least or not purposes:
            return None
        purpose, _ = purposes.most_common(1)[0]
        return None if purpose == "base" else purpose

    async def suppressed(self, purpose: str, village_id: int, hours: float) -> bool:
        row = await self.lessons.get(suppression_key(purpose, village_id))
        return row is not None and _now() - row.last_seen < timedelta(hours=hours)

    async def run(self) -> list[str]:
        knobs = await KnobStore(self.session).load()
        least = knobs.int("watch.stuck_rounds")
        hours = knobs.get("watch.suppress_hours")
        repo = CoordinationRepository(self.session)
        done = []
        for latest in await repo.latest():
            rows = await repo.history(latest.village_id, limit=knobs.int("watch.rounds"))
            rounds = [json.loads(r.data) if isinstance(r.data, str) else (r.data or {}) for r in rows]
            purpose = self.blocker(rounds, least)
            if purpose is None or await self.suppressed(purpose, latest.village_id, hours):
                continue
            text = f"reserva {purpose} segurou o estoque com a fila de obras parada em {least}+ rodadas; suspensa por {hours:g}h"
            await self.lessons.observe(suppression_key(purpose, latest.village_id), "watch", f"vigia: {purpose} suspensa", text, {"purpose": purpose})
            logger.warning("Vigia: aldeia {} — {}", latest.village_id, text)
            done.append(text)
        return done
