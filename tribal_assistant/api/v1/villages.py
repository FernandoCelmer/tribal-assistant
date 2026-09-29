"""Village endpoints."""

from fastapi import APIRouter, Depends

from tribal_assistant.schemas.village import Village, VillageCreate, VillageUpdate
from tribal_assistant.services.villages import VillageService

villages_router = APIRouter()


@villages_router.get("", response_model=list[Village])
async def list_villages(service: VillageService = Depends(VillageService)) -> list[Village]:
    rows = await service.list()
    return [Village.model_validate(row) for row in rows]


@villages_router.post("", response_model=Village, status_code=201)
async def upsert_village(
    body: VillageCreate,
    service: VillageService = Depends(VillageService),
) -> Village:
    return Village.model_validate(await service.upsert(body))


@villages_router.get("/{village_id}", response_model=Village)
async def get_village(
    village_id: int,
    service: VillageService = Depends(VillageService),
) -> Village:
    return Village.model_validate(await service.get(village_id))


@villages_router.patch("/{village_id}", response_model=Village)
async def update_village(
    village_id: int,
    body: VillageUpdate,
    service: VillageService = Depends(VillageService),
) -> Village:
    return Village.model_validate(await service.update(village_id, body))
