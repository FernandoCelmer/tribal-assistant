"""World data endpoints."""

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.schemas.world import NearbyVillage, WorldStatus
from app.services.world import WorldService

world_router = APIRouter()


@world_router.get("/status", response_model=WorldStatus)
async def status(service: WorldService = Depends(WorldService)) -> WorldStatus:
    return await service.status()


@world_router.get("/nearby", response_model=list[NearbyVillage])
async def nearby(
    village_id: int | None = None,
    kind: Literal["barbarian", "player", "all"] = "barbarian",
    radius: int = Query(default=15, ge=1, le=100),
    limit: int = Query(default=50, ge=1, le=500),
    service: WorldService = Depends(WorldService),
) -> list[NearbyVillage]:
    return await service.nearby(village_id, kind, radius, limit)
