"""Agents dashboard: live status, rounds with full trace, statistics, logs and village history."""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.trace import RunTrace
from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.core.events import event_bus
from tribal_assistant.core.repositories.agent_settings import AgentSettingsRepository
from tribal_assistant.core.repositories.game import GameRepository
from tribal_assistant.core.repositories.observability import ObservabilityRepository
from tribal_assistant.core.schemas.observability import (
    DecisionOut,
    FlowOut,
    LiveOut,
    LogOut,
    RunDetailOut,
    RunOut,
    SnapshotOut,
    StatsOut,
    StepOut,
)

HEARTBEAT_SECONDS = 15


class ObservabilityService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = ObservabilityRepository(session)
        self.settings = AgentSettingsRepository(session)
        self.game = GameRepository(session)

    async def live(self) -> LiveOut:
        config = await self.settings.get()
        last = await self.settings.last_run_at()
        next_run = None

        if config.enabled:
            next_run = (last + timedelta(minutes=config.interval_minutes)) if last else self.repository.now()

        current = RunTrace.live
        if current is None:
            running = [r for r in await self.repository.runs(limit=5) if r.status == "running"]
            if running:
                current = {"run_id": running[0].run_id, "started_at": running[0].started_at.isoformat(), "step": "rodando em outro processo"}

        return LiveOut(
            running=current is not None,
            enabled=config.enabled,
            next_run_at=next_run,
            **(current or {}),
        )

    async def runs(self, limit: int) -> list[RunOut]:
        return [RunOut.model_validate(r) for r in await self.repository.runs(limit)]

    async def run(self, run_id: str) -> RunDetailOut:
        run = await self.repository.run(run_id)
        if run is None:
            raise NotFoundError(f"rodada {run_id} não encontrada")

        return RunDetailOut(
            run=RunOut.model_validate(run),
            villages=await self.repository.village_names(),
            steps=[StepOut.model_validate(s) for s in await self.repository.steps(run_id)],
            decisions=[DecisionOut.model_validate(d) for d in await self.repository.decisions(run_id)],
        )

    async def stats(self, hours: int) -> StatsOut:
        return StatsOut.model_validate(await self.repository.stats(hours))

    async def flow(self, hours: int, run_id: str | None) -> FlowOut:
        return FlowOut.model_validate(await self.repository.flow(hours, run_id))

    async def logs(self, level: str, limit: int, query: str | None, before_id: int | None) -> list[LogOut]:
        rows = await self.repository.logs(level, limit, query, before_id)
        return [LogOut.model_validate(r) for r in rows]

    async def history(self, village_id: int | None, hours: int) -> list[SnapshotOut]:
        since = self.repository.now() - timedelta(hours=hours)
        return [SnapshotOut.model_validate(s) for s in await self.game.snapshots(village_id, since)]


class EventStream:
    """Server-Sent Events: every bus event as it happens, with heartbeats to keep the connection open."""

    async def __call__(self) -> AsyncIterator[str]:
        queue = event_bus.subscribe()

        try:
            yield "retry: 3000\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    yield ": ping\n\n"
                    continue

                payload = json.dumps({"at": event.at, **event.data}, ensure_ascii=False, default=str)
                yield f"event: {event.kind}\ndata: {payload}\n\n"
        finally:
            event_bus.unsubscribe(queue)
