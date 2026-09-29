"""Game state endpoints."""

from fastapi import APIRouter

from tribal_assistant.api.deps import GameServiceDep
from tribal_assistant.core.schemas.game import GameOverview

game_router = APIRouter()


@game_router.get("/overview", response_model=GameOverview)
async def overview(service: GameServiceDep) -> GameOverview:
    return await service.overview()
