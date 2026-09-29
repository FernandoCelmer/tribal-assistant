"""Create, list and toggle game accounts."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.accounts.registry import AccountRegistry
from tribal_assistant.core.crypto import vault
from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.db.session import get_session
from tribal_assistant.repositories.accounts import AccountRepository
from tribal_assistant.schemas.accounts import AccountIn, AccountOut, AccountUpdate


class AccountService:
    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        self.repo = AccountRepository(session)
        self.registry = AccountRegistry(session)

    async def list(self) -> list[AccountOut]:
        return [AccountOut.model_validate(a) for a in await self.repo.list()]

    async def create(self, body: AccountIn) -> AccountOut:
        server = body.world_url.split("//", 1)[-1].split(".", 1)[0]
        account = await self.registry.create(
            body.name or f"{body.username} ({server})", server, body.world_url, body.username, body.password, body.headless
        )
        return AccountOut.model_validate(account)

    async def update(self, account_id: int, body: AccountUpdate) -> AccountOut:
        account = await self.repo.get(account_id)
        if account is None:
            raise NotFoundError(f"conta {account_id} não existe")

        if body.name is not None:
            account.name = body.name
        if body.password is not None:
            account.password = vault().encrypt(body.password)
        if body.headless is not None:
            account.headless = body.headless
        if body.enabled is not None:
            account.enabled = body.enabled

        return AccountOut.model_validate(await self.repo.save(account))
