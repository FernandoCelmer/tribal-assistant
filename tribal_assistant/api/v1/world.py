"""World data endpoints."""

from dataclasses import asdict
from typing import Any, Literal

from fastapi import APIRouter, Query

from tribal_assistant.api.deps import WorldServiceDep
from tribal_assistant.core.schemas.world import NearbyVillage, WorldStatus

world_router = APIRouter()


@world_router.get("/status", response_model=WorldStatus)
async def status(service: WorldServiceDep) -> WorldStatus:
    return await service.status()


@world_router.get("/config", response_model=dict[str, Any])
async def config(service: WorldServiceDep) -> dict[str, Any]:
    return asdict(await service.config())


@world_router.get("/nearby", response_model=list[NearbyVillage])
async def nearby(
    service: WorldServiceDep,
    village_id: int | None = None,
    kind: Literal["barbarian", "player", "all"] = "barbarian",
    radius: int = Query(default=15, ge=1, le=100),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[NearbyVillage]:
    return await service.nearby(village_id, kind, radius, limit)


@world_router.post("/sync", response_model=WorldStatus)
async def sync(service: WorldServiceDep) -> WorldStatus:
    from tribal_assistant.core.game.modules.world_sync import sync_world

    await sync_world()
    return await service.status()
