"""Assistant control endpoints."""

from fastapi import APIRouter, Depends

from app.schemas.assistant import CommandResult, AssistantStatus
from app.services.assistant import AssistantService

assistant_router = APIRouter()


def _service() -> AssistantService:
    return AssistantService()


@assistant_router.get("/status", response_model=AssistantStatus)
async def status(service: AssistantService = Depends(_service)) -> AssistantStatus:
    return await service.status()


@assistant_router.post("/start", response_model=CommandResult)
async def start(service: AssistantService = Depends(_service)) -> CommandResult:
    return await service.start()


@assistant_router.post("/stop", response_model=CommandResult)
async def stop(service: AssistantService = Depends(_service)) -> CommandResult:
    return await service.stop()


@assistant_router.post("/sync", response_model=CommandResult)
async def sync(service: AssistantService = Depends(_service)) -> CommandResult:
    return await service.sync()
