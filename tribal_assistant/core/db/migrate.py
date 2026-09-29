"""Copies an existing database (old single-account SQLite or another server) into the multi-account schema."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import Engine, MetaData, create_engine, func, insert, inspect, select, text

from tribal_assistant.core.config import settings
from tribal_assistant.core.crypto import vault
from tribal_assistant.core.db.base import Base

SYNC_DRIVERS = {"sqlite+aiosqlite": "sqlite", "postgresql+asyncpg": "postgresql+psycopg"}
CHUNK = 2000


def sync_url(url: str) -> str:
    scheme, sep, rest = url.partition("://")
    return f"{SYNC_DRIVERS.get(scheme, scheme)}{sep}{rest}"


@dataclass
class CopyReport:
    tables: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)


class DatabaseCopier:
    """Creates the current schema on the target and copies every row, filling account and world."""

    def __init__(self, source_url: str, target_url: str) -> None:
        self.source: Engine = create_engine(sync_url(source_url))
        self.target: Engine = create_engine(sync_url(target_url))

    def run(self, wipe: bool = False) -> CopyReport:
        from tribal_assistant.core import models  # noqa: F401

        if wipe:
            Base.metadata.drop_all(self.target)
        Base.metadata.create_all(self.target)

        source_meta = MetaData()
        source_meta.reflect(self.source)
        report = CopyReport()

        account_id, world = self._account(source_meta)
        for table in Base.metadata.sorted_tables:
            if table.name == "accounts" and "accounts" not in source_meta.tables:
                continue

            if table.name not in source_meta.tables:
                report.skipped.append(table.name)
                continue

            count = self._copy(source_meta.tables[table.name], table, account_id, world)
            report.tables[table.name] = count
            logger.info("{} linha(s) copiadas para {}", count, table.name)

        self._reset_sequences()
        return report

    def _account(self, source_meta: MetaData) -> tuple[int, str]:
        """Account and world the old single-account rows belong to; creates account 1 from .env when missing."""
        with self.target.begin() as conn:
            existing = conn.execute(select(Base.metadata.tables["accounts"].c.id, Base.metadata.tables["accounts"].c.server).order_by("id")).first()
            if existing is not None:
                return existing.id, existing.server

            if "accounts" in source_meta.tables:
                with self.source.connect() as src:
                    row = src.execute(select(source_meta.tables["accounts"]).order_by("id")).first()
                if row is not None:
                    return row.id, row.server

            if not (settings.tw_world_url and settings.tw_username and settings.tw_password):
                raise RuntimeError("defina TW_WORLD_URL, TW_USERNAME e TW_PASSWORD no .env para criar a conta 1")

            conn.execute(
                insert(Base.metadata.tables["accounts"]).values(
                    id=1,
                    name=f"{settings.tw_username} ({settings.tw_server})",
                    server=settings.tw_server,
                    world_url=settings.tw_world_url.rstrip("/"),
                    username=settings.tw_username,
                    password=vault().encrypt(settings.tw_password),
                    headless=settings.headless,
                    enabled=True,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            return 1, settings.tw_server

    def _rows(self, source_table, columns: list[str]) -> Iterator[list[dict]]:
        with self.source.connect() as src:
            result = src.execution_options(stream_results=True).execute(select(*(source_table.c[c] for c in columns)))
            while batch := result.fetchmany(CHUNK):
                yield [dict(row._mapping) for row in batch]

    def _copy(self, source_table, target_table, account_id: int, world: str) -> int:
        shared = [c.name for c in target_table.columns if c.name in source_table.columns]
        fills = {}
        if "account_id" in target_table.columns and "account_id" not in source_table.columns:
            fills["account_id"] = account_id
        if "world" in target_table.columns and "world" not in source_table.columns:
            fills["world"] = world

        with self.target.begin() as conn:
            if conn.execute(select(func.count()).select_from(target_table)).scalar():
                logger.warning("{} já tem linhas; ignorada", target_table.name)
                return 0

        total = 0
        for batch in self._rows(source_table, shared):
            rows = [{**row, **fills} for row in batch]
            with self.target.begin() as conn:
                conn.execute(insert(target_table), rows)
            total += len(rows)

        return total

    def _reset_sequences(self) -> None:
        if self.target.dialect.name != "postgresql":
            return

        with self.target.begin() as conn:
            for table in Base.metadata.sorted_tables:
                column = table.columns.get("id")
                if column is None or not self._integer(column):
                    continue

                conn.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table.name}), 0) + 1, false)"
                    )
                )

    @staticmethod
    def _integer(column) -> bool:
        try:
            return column.type.python_type is int
        except NotImplementedError:
            return False

    def tables(self) -> list[str]:
        return inspect(self.target).get_table_names()
