"""Only one engine plays at a time: a PostgreSQL advisory lock held for the engine's lifetime."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

LOCK_KEY = 7_311_144


class EngineLease:
    def __init__(self, engine: AsyncEngine, key: int = LOCK_KEY) -> None:
        self.engine = engine
        self.key = key
        self.connection: AsyncConnection | None = None

    @property
    def shared(self) -> bool:
        return self.engine.dialect.name == "postgresql"

    async def acquire(self) -> bool:
        if not self.shared:
            return True

        if self.connection is not None:
            return True

        connection = await self.engine.connect()
        held = (await connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": self.key})).scalar()
        await connection.commit()
        if not held:
            await connection.close()
            return False

        self.connection = connection
        return True

    async def release(self) -> None:
        if self.connection is None:
            return

        try:
            await self.connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": self.key})
            await self.connection.commit()
        finally:
            await self.connection.close()
            self.connection = None
