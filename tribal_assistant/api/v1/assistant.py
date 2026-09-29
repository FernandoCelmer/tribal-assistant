"""Assistant control endpoints."""

from fastapi import APIRouter

from tribal_assistant.api.deps import AssistantServiceDep
from tribal_assistant.core.schemas.assistant import AssistantStatus, CommandResult

assistant_router = APIRouter()


@assistant_router.get("/status", response_model=AssistantStatus)
async def status(service: AssistantServiceDep) -> AssistantStatus:
    return await service.status()


@assistant_router.post("/sync", response_model=CommandResult)
async def sync(service: AssistantServiceDep) -> CommandResult:
    return await service.sync()
