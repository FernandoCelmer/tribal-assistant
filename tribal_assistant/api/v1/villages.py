"""Village endpoints."""

from fastapi import APIRouter

from tribal_assistant.api.deps import VillageServiceDep
from tribal_assistant.core.schemas.village import Village, VillageCreate, VillageUpdate

villages_router = APIRouter()


@villages_router.get("", response_model=list[Village])
async def list_villages(service: VillageServiceDep) -> list[Village]:
    rows = await service.list()
    return [Village.model_validate(row) for row in rows]


@villages_router.post("", response_model=Village, status_code=201)
async def upsert_village(
    service: VillageServiceDep,
    body: VillageCreate,
) -> Village:
    return Village.model_validate(await service.upsert(body))


@villages_router.get("/{village_id}", response_model=Village)
async def get_village(
    service: VillageServiceDep,
    village_id: int,
) -> Village:
    return Village.model_validate(await service.get(village_id))


@villages_router.patch("/{village_id}", response_model=Village)
async def update_village(
    service: VillageServiceDep,
    village_id: int,
    body: VillageUpdate,
) -> Village:
    return Village.model_validate(await service.update(village_id, body))
