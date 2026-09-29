"""Farm endpoints."""

from fastapi import APIRouter, Depends

from tribal_assistant.core.schemas.farm import FarmTarget, FarmTargetCreate, FarmTickResult
from tribal_assistant.core.services.farm import FarmService

farm_router = APIRouter()


@farm_router.get("/targets", response_model=list[FarmTarget])
async def list_targets(service: FarmService = Depends(FarmService)) -> list[FarmTarget]:
    rows = await service.list()
    return [FarmTarget.model_validate(row) for row in rows]


@farm_router.post("/targets", response_model=FarmTarget, status_code=201)
async def add_target(
    body: FarmTargetCreate,
    service: FarmService = Depends(FarmService),
) -> FarmTarget:
    return FarmTarget.model_validate(await service.add(body))


@farm_router.post("/tick", response_model=FarmTickResult)
async def farm_tick(service: FarmService = Depends(FarmService)) -> FarmTickResult:
    return await service.tick()
