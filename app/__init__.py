"""Tribal Wars bot — FastAPI application factory."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.health import health_router
from app.api.v1 import v1_router
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.db.session import init_db
from app.scheduler.runtime import scheduler

__version__ = "0.1.0"

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    await init_db()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Tribal Wars Bot",
        description="Automation control plane for Tribal Wars.",
        version=__version__,
        lifespan=lifespan,
    )

    install_error_handlers(application)
    application.include_router(health_router)
    application.include_router(v1_router, prefix=API_V1_PREFIX)

    return application


app = create_app()
