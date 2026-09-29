"""Turns stored accounts into runtime contexts and bootstraps the first account from .env."""

import shutil
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.accounts.context import AccountContext
from tribal_assistant.core.config import settings
from tribal_assistant.core.crypto import vault
from tribal_assistant.models.account import Account
from tribal_assistant.repositories.accounts import AccountRepository


class AccountRegistry:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AccountRepository(session)

    @staticmethod
    def context(account: Account) -> AccountContext:
        return AccountContext(
            id=account.id,
            name=account.name,
            server=account.server,
            world_url=account.world_url,
            username=account.username,
            password=vault().decrypt(account.password),
            headless=account.headless,
        )

    async def contexts(self, enabled_only: bool = True) -> list[AccountContext]:
        return [self.context(a) for a in await self.repo.list(enabled_only)]

    async def find(self, account_id: int | None) -> AccountContext | None:
        if account_id is not None:
            account = await self.repo.get(account_id)
            if account is not None:
                return self.context(account)

        accounts = await self.repo.list(enabled_only=True) or await self.repo.list()
        return self.context(accounts[0]) if accounts else None

    async def create(self, name: str, server: str, world_url: str, username: str, password: str, headless: bool = False) -> Account:
        return await self.repo.add(
            name=name,
            server=server,
            world_url=world_url.rstrip("/"),
            username=username,
            password=vault().encrypt(password),
            headless=headless,
            enabled=True,
        )

    async def bootstrap(self) -> None:
        """Creates account 1 from TW_* in .env the first time, keeping the saved browser session."""
        if await self.repo.list() or not (settings.tw_world_url and settings.tw_username and settings.tw_password):
            return

        account = await self.create(
            name=f"{settings.tw_username} ({settings.tw_server})",
            server=settings.tw_server,
            world_url=settings.tw_world_url,
            username=settings.tw_username,
            password=settings.tw_password,
            headless=settings.headless,
        )
        legacy = Path(settings.browser_state_path)
        target = self.context(account).state_path
        if legacy.exists() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(legacy, target)

        logger.info("Account {} created from .env", account.name)
