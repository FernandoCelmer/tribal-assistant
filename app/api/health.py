"""Health endpoint."""

from fastapi import APIRouter

from app.schemas.health import Health

health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=Health)
async def health() -> Health:
    from app import __version__

    return Health(status="ok", version=__version__)
