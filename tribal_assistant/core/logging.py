"""Loguru bootstrap: stderr plus the database log store."""

import atexit
import sys

from loguru import logger

from tribal_assistant.core.config import settings
from tribal_assistant.core.log_store import LogStore

FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


class LoggingSetup:
    store: LogStore | None = None

    @classmethod
    def configure(cls, level: str = "INFO", persist: bool = True) -> None:
        logger.remove()
        logger.add(sys.stderr, level=level, format=FORMAT)

        if not persist:
            return

        if cls.store is None:
            store = LogStore(settings.database_url, retention_days=settings.log_retention_days)
            if not store.start():
                return
            cls.store = store
            atexit.register(store.stop)

        logger.add(cls.store.sink, level=settings.log_store_level, format="{message}")


def configure_logging(level: str = "INFO", persist: bool = True) -> None:
    LoggingSetup.configure(level, persist)
