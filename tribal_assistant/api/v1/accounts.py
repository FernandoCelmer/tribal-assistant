"""Game account endpoints."""

from fastapi import APIRouter, Depends

from tribal_assistant.core.schemas.accounts import AccountIn, AccountOut, AccountUpdate
from tribal_assistant.core.services.accounts import AccountService

accounts_router = APIRouter()


@accounts_router.get("", response_model=list[AccountOut])
async def list_accounts(service: AccountService = Depends(AccountService)) -> list[AccountOut]:
    return await service.list()


@accounts_router.post("", response_model=AccountOut, status_code=201)
async def create_account(body: AccountIn, service: AccountService = Depends(AccountService)) -> AccountOut:
    return await service.create(body)


@accounts_router.patch("/{account_id}", response_model=AccountOut)
async def update_account(account_id: int, body: AccountUpdate, service: AccountService = Depends(AccountService)) -> AccountOut:
    return await service.update(account_id, body)
