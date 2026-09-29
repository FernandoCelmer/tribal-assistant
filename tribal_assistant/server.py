"""FastAPI application factory: API, dashboard and scheduler lifespan."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tribal_assistant.api.errors import install_error_handlers
from tribal_assistant.api.health import health_router
from tribal_assistant.api.pages import WebPages
from tribal_assistant.api.v1 import v1_router
from tribal_assistant.core.config import settings
from tribal_assistant.core.db.session import init_db
from tribal_assistant.core.events import event_bus
from tribal_assistant.core.game.session import game_session
from tribal_assistant.core.logging import configure_logging
from tribal_assistant.core.scheduler.runtime import scheduler
from tribal_assistant.version import __version__

API_V1_PREFIX = "/api/v1"
WEB_DIR = Path(__file__).parent / "web"
async def _interrupt_leftover_runs() -> None:
    from tribal_assistant.core.db.session import SessionFactory
    from tribal_assistant.core.repositories.observability import ObservabilityRepository

    async with SessionFactory() as session:
        await ObservabilityRepository(session).interrupt_stale(older_than_minutes=0)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    event_bus.bind(asyncio.get_running_loop())
    await init_db()
    await _interrupt_leftover_runs()
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

    WebPages(WEB_DIR).register(application)

    return application


app = create_app()
