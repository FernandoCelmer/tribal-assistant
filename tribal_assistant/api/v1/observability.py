"""Agents dashboard endpoints: live status, rounds, trace, stats, logs, history and the event stream."""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from tribal_assistant.api.deps import ObservabilityServiceDep
from tribal_assistant.core.schemas.observability import (
    FlowOut,
    LiveOut,
    LogOut,
    RunDetailOut,
    RunOut,
    SnapshotOut,
    StatsOut,
)
from tribal_assistant.core.services.observability import EventStream

observability_router = APIRouter()


@observability_router.get("/agents/live", response_model=LiveOut)
async def live(service: ObservabilityServiceDep) -> LiveOut:
    return await service.live()


@observability_router.get("/agents/runs", response_model=list[RunOut])
async def runs(
    service: ObservabilityServiceDep,
    limit: int = Query(default=30, ge=1, le=200),
) -> list[RunOut]:
    return await service.runs(limit)


@observability_router.get("/agents/runs/{run_id}", response_model=RunDetailOut)
async def run_detail(run_id: str, service: ObservabilityServiceDep) -> RunDetailOut:
    return await service.run(run_id)


@observability_router.get("/agents/stats", response_model=StatsOut)
async def stats(
    service: ObservabilityServiceDep,
    hours: int = Query(default=24, ge=1, le=720),
) -> StatsOut:
    return await service.stats(hours)


@observability_router.get("/agents/flow", response_model=FlowOut)
async def flow(
    service: ObservabilityServiceDep,
    hours: int = Query(default=24, ge=1, le=720),
    run_id: str | None = None,
) -> FlowOut:
    return await service.flow(hours, run_id)


@observability_router.get("/logs", response_model=list[LogOut])
async def logs(
    service: ObservabilityServiceDep,
    level: str = Query(default="INFO"),
    limit: int = Query(default=200, ge=1, le=2000),
    q: str | None = None,
    before_id: int | None = None,
) -> list[LogOut]:
    return await service.logs(level, limit, q, before_id)


@observability_router.get("/game/history", response_model=list[SnapshotOut])
async def history(
    service: ObservabilityServiceDep,
    village_id: int | None = None,
    hours: int = Query(default=168, ge=1, le=2160),
) -> list[SnapshotOut]:
    return await service.history(village_id, hours)


@observability_router.get("/events")
async def events() -> StreamingResponse:
    return StreamingResponse(
        EventStream()(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
