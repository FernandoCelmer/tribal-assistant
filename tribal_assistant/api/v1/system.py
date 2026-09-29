"""Runtime configuration that lives outside the database."""

from fastapi import APIRouter

from tribal_assistant.schemas.system import SystemInfo
from tribal_assistant.services.system import SystemService

system_router = APIRouter()


@system_router.get("/info", response_model=SystemInfo)
async def info() -> SystemInfo:
    return SystemService().info()
