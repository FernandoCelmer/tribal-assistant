from sqlalchemy.ext.asyncio import create_async_engine

from tribal_assistant.core.db.lease import EngineLease


async def test_sqlite_has_a_single_server_so_the_lease_is_always_granted() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    lease = EngineLease(engine)

    assert lease.shared is False
    assert await lease.acquire() is True
    await lease.release()
    await engine.dispose()
