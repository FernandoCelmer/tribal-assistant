"""Assistant control endpoints."""

from fastapi import APIRouter, Depends

from tribal_assistant.core.schemas.assistant import AssistantStatus, CommandResult
from tribal_assistant.core.services.assistant import AssistantService

assistant_router = APIRouter()


def _service() -> AssistantService:
    return AssistantService()


@assistant_router.get("/status", response_model=AssistantStatus)
async def status(service: AssistantService = Depends(_service)) -> AssistantStatus:
    return await service.status()


@assistant_router.post("/sync", response_model=CommandResult)
async def sync(service: AssistantService = Depends(_service)) -> CommandResult:
    return await service.sync()
