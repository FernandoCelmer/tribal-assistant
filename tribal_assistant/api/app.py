"""FastAPI application: the API over the core engine."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from tribal_assistant.api.errors import install_error_handlers
from tribal_assistant.api.health import health_router
from tribal_assistant.api.v1 import v1_router
from tribal_assistant.core.runtime import engine
from tribal_assistant.version import __version__

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await engine.start()
    try:
        yield
    finally:
        await engine.stop()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Tribal Assistant",
        description="API over the Tribal Assistant engine: accounts, game state, agents and observability.",
        version=__version__,
        lifespan=lifespan,
    )

    install_error_handlers(application)
    application.include_router(health_router)
    application.include_router(v1_router, prefix=API_V1_PREFIX)

    return application


app = create_app()
