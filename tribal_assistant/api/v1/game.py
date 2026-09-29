"""Game state endpoints."""

from fastapi import APIRouter, Query

from tribal_assistant.api.deps import (
    ForecastServiceDep,
    GameServiceDep,
    LiveGameServiceDep,
    ReportServiceDep,
)
from tribal_assistant.core.schemas.game import GameOverview
from tribal_assistant.core.schemas.insight import ScavengePlan, VillageForecast
from tribal_assistant.core.schemas.market import InventoryOut, KnightOut, MarketOut
from tribal_assistant.core.schemas.reports import ReportPage

game_router = APIRouter()


@game_router.get("/overview", response_model=GameOverview)
async def overview(service: GameServiceDep) -> GameOverview:
    return await service.overview()


@game_router.get("/reports", response_model=ReportPage)
async def reports(
    service: ReportServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    category: str | None = None,
    result: str | None = None,
    coords: str | None = None,
) -> ReportPage:
    return await service.page(offset, limit, category, result, coords)


@game_router.get("/forecast", response_model=list[VillageForecast])
async def forecast(
    service: ForecastServiceDep,
    village_id: int | None = None,
    wood: int = Query(default=0, ge=0),
    clay: int = Query(default=0, ge=0),
    iron: int = Query(default=0, ge=0),
) -> list[VillageForecast]:
    return await service.villages(village_id, {"wood": wood, "clay": clay, "iron": iron})


@game_router.get("/scavenge-plan", response_model=list[ScavengePlan])
async def scavenge_plan(service: ForecastServiceDep, village_id: int | None = None) -> list[ScavengePlan]:
    return await service.scavenge(village_id)


@game_router.get("/market", response_model=MarketOut)
async def market(service: LiveGameServiceDep, village_id: int | None = None) -> MarketOut:
    return await service.market(village_id)


@game_router.get("/knight", response_model=KnightOut)
async def knight(service: LiveGameServiceDep, village_id: int | None = None) -> KnightOut:
    return await service.knight(village_id)


@game_router.get("/inventory", response_model=InventoryOut)
async def inventory(service: LiveGameServiceDep, village_id: int | None = None) -> InventoryOut:
    return await service.inventory(village_id)
