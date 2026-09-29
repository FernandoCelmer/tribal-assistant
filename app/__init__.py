"""Tribal Assistant — FastAPI application factory."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.health import health_router
from app.api.v1 import v1_router
from app.client.session import game_session
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.db.session import init_db
from app.scheduler.runtime import scheduler

__version__ = "0.1.0"

API_V1_PREFIX = "/api/v1"
WEB_DIR = Path(__file__).parent / "web"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    await init_db()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await game_session.close()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Tribal Assistant",
        description="Automation control plane for Tribal Wars.",
        version=__version__,
        lifespan=lifespan,
    )

    install_error_handlers(application)
    application.include_router(health_router)
    application.include_router(v1_router, prefix=API_V1_PREFIX)

    @application.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    return application


app = create_app()
