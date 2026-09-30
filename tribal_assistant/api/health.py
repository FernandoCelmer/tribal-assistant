"""Health endpoint."""

from fastapi import APIRouter

from tribal_assistant.core.schemas.health import Health
from tribal_assistant.version import __version__

health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=Health)
async def health() -> Health:
    return Health(status="ok", version=__version__)
