"""Game state endpoints."""

from fastapi import APIRouter, Depends

from app.schemas.game import GameOverview
from app.services.game import GameService

game_router = APIRouter()


@game_router.get("/overview", response_model=GameOverview)
async def overview(service: GameService = Depends(GameService)) -> GameOverview:
    return await service.overview()
