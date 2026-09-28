"""Bot control endpoints."""

from fastapi import APIRouter, Depends

from app.schemas.bot import BotCommandResult, BotStatus
from app.services.bot import BotService

bot_router = APIRouter()


def _service() -> BotService:
    return BotService()


@bot_router.get("/status", response_model=BotStatus)
async def status(service: BotService = Depends(_service)) -> BotStatus:
    return await service.status()


@bot_router.post("/start", response_model=BotCommandResult)
async def start(service: BotService = Depends(_service)) -> BotCommandResult:
    return await service.start()


@bot_router.post("/stop", response_model=BotCommandResult)
async def stop(service: BotService = Depends(_service)) -> BotCommandResult:
    return await service.stop()
