"""Game state endpoints."""

from fastapi import APIRouter, Depends

from tribal_assistant.core.schemas.game import GameOverview
from tribal_assistant.core.services.game import GameService

game_router = APIRouter()


@game_router.get("/overview", response_model=GameOverview)
async def overview(service: GameService = Depends(GameService)) -> GameOverview:
    return await service.overview()
