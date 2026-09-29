"""Loguru sink that keeps log lines in the database and streams them to the dashboard."""

import os
import queue
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, delete, insert
from sqlalchemy.engine import Engine

from tribal_assistant.core.accounts.context import current_account_id
from tribal_assistant.core.events import event_bus
from tribal_assistant.core.models.log import AppLog

SYNC_DRIVERS = {"sqlite+aiosqlite": "sqlite", "postgresql+asyncpg": "postgresql+psycopg"}


class LogStore:
    """Buffers records from any thread and writes them in batches from one worker thread."""

    def __init__(self, database_url: str, retention_days: int = 14, batch: int = 50, interval: float = 1.5) -> None:
        self.database_url = database_url
        self.retention_days = retention_days
        self.batch = batch
        self.interval = interval
        self.process = f"{os.path.basename(os.sys.argv[0])[:16]}:{os.getpid()}"
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=20_000)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._engine: Engine | None = None

    def _sync_url(self) -> str | None:
        scheme, _, rest = self.database_url.partition("://")
        driver = SYNC_DRIVERS.get(scheme)
        return f"{driver}://{rest}" if driver else None

    def start(self) -> bool:
        url = self._sync_url()
        if url is None or self._thread is not None:
            return False

        try:
            connect_args = {"timeout": 30} if url.startswith("sqlite") else {}
            self._engine = create_engine(url, connect_args=connect_args)
            AppLog.__table__.create(self._engine, checkfirst=True)
        except Exception:
            self._engine = None
            return False

        self._thread = threading.Thread(target=self._work, name="log-store", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def sink(self, message: Any) -> None:
        record = message.record
        row = {
            "at": record["time"].astimezone(UTC).replace(tzinfo=None),
            "level": record["level"].name,
            "source": f"{record['name']}:{record['function']}:{record['line']}"[:160],
            "message": record["message"],
            "process": self.process,
            "account_id": current_account_id(),
        }

        try:
            self._queue.put_nowait(row)
        except queue.Full:
            return

        event_bus.publish(
            "log",
            {**row, "at": row["at"].isoformat(timespec="seconds")},
        )

    def _work(self) -> None:
        last_prune = datetime.min

        while not self._stop.is_set() or not self._queue.empty():
            rows = self._drain()
            if rows:
                self._write(rows)

            if datetime.now() - last_prune > timedelta(hours=6):
                self._prune()
                last_prune = datetime.now()

            self._stop.wait(self.interval)

    def _drain(self) -> list[dict[str, Any]]:
        rows = []
        while len(rows) < self.batch * 20:
            try:
                rows.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return rows

    def _write(self, rows: list[dict[str, Any]]) -> None:
        if self._engine is None:
            return

        try:
            with self._engine.begin() as conn:
                conn.execute(insert(AppLog), rows)
        except Exception:
            return

    def _prune(self) -> None:
        if self._engine is None:
            return

        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=self.retention_days)
        try:
            with self._engine.begin() as conn:
                conn.execute(delete(AppLog).where(AppLog.at < cutoff))
        except Exception:
            return
