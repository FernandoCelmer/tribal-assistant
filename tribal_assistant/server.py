"""FastAPI application factory: API, dashboard and scheduler lifespan."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tribal_assistant import __version__
from tribal_assistant.api.health import health_router
from tribal_assistant.api.v1 import v1_router
from tribal_assistant.client.session import game_session
from tribal_assistant.core.config import settings
from tribal_assistant.core.errors import install_error_handlers
from tribal_assistant.core.logging import configure_logging
from tribal_assistant.db.session import init_db
from tribal_assistant.scheduler.runtime import scheduler

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

    application.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

    @application.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    @application.get("/design", include_in_schema=False)
    async def design_system() -> FileResponse:
        return FileResponse(WEB_DIR / "design.html", headers={"Cache-Control": "no-cache"})

    return application


app = create_app()
