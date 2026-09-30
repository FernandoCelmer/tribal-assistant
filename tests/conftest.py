"""Test fixtures — in-memory SQLite session + FastAPI client."""

from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tribal_assistant.api.app import app as fastapi_app
from tribal_assistant.api.deps import get_session
from tribal_assistant.core import models  # noqa: F401
from tribal_assistant.core.accounts.context import AccountContext, use_account
from tribal_assistant.core.db.base import Base


@pytest.fixture(autouse=True)
def account_context() -> Iterator[AccountContext]:
    account = AccountContext(id=1, name="teste", server="br144", world_url="https://br144.example", username="u", password="p")
    with use_account(account):
        yield account


@pytest.fixture
async def test_engine() -> AsyncIterator:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(test_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s


@pytest.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override() -> AsyncIterator[AsyncSession]:
        yield session

    fastapi_app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    fastapi_app.dependency_overrides.clear()
