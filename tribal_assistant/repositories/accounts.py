"""Data access for game accounts; never filtered by the current account."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.models.account import Account


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, enabled_only: bool = False) -> Sequence[Account]:
        stmt = select(Account).order_by(Account.id)
        if enabled_only:
            stmt = stmt.where(Account.enabled.is_(True))

        return (await self.session.execute(stmt)).scalars().all()

    async def get(self, account_id: int) -> Account | None:
        return await self.session.get(Account, account_id)

    async def add(self, **fields: object) -> Account:
        account = Account(created_at=datetime.now(UTC).replace(tzinfo=None), **fields)
        self.session.add(account)
        await self.session.commit()
        return account

    async def save(self, account: Account) -> Account:
        await self.session.commit()
        return account

    async def delete(self, account: Account) -> None:
        await self.session.delete(account)
        await self.session.commit()
