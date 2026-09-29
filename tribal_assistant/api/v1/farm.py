"""Farm endpoints."""

from fastapi import APIRouter

from tribal_assistant.api.deps import FarmServiceDep
from tribal_assistant.core.schemas.farm import FarmTarget, FarmTargetCreate, FarmTickResult

farm_router = APIRouter()


@farm_router.get("/targets", response_model=list[FarmTarget])
async def list_targets(service: FarmServiceDep) -> list[FarmTarget]:
    rows = await service.list()
    return [FarmTarget.model_validate(row) for row in rows]


@farm_router.post("/targets", response_model=FarmTarget, status_code=201)
async def add_target(
    service: FarmServiceDep,
    body: FarmTargetCreate,
) -> FarmTarget:
    return FarmTarget.model_validate(await service.add(body))


@farm_router.post("/tick", response_model=FarmTickResult)
async def farm_tick(service: FarmServiceDep) -> FarmTickResult:
    return await service.tick()
