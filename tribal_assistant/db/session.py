"""Async engine + session factory."""

from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tribal_assistant.core.config import settings
from tribal_assistant.db.base import Base


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite"):
        path = url.split("///", 1)[-1]
        Path(path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    from tribal_assistant import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from tribal_assistant.accounts.registry import AccountRegistry

    async with SessionFactory() as session:
        await AccountRegistry(session).bootstrap()


ACCOUNT_COOKIE = "tw_account"


def requested_account(request: Request) -> int | None:
    raw = request.query_params.get("account") or request.headers.get("x-account") or request.cookies.get(ACCOUNT_COOKIE)
    return int(raw) if raw and raw.isdigit() else None


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    from tribal_assistant.accounts.context import use_account
    from tribal_assistant.accounts.registry import AccountRegistry

    async with SessionFactory() as session:
        account = await AccountRegistry(session).find(requested_account(request))
        if account is None:
            yield session
            return

        with use_account(account):
            yield session
