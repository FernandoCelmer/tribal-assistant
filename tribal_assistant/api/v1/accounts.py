"""Game account endpoints."""

from fastapi import APIRouter

from tribal_assistant.api.deps import AccountServiceDep
from tribal_assistant.core.schemas.accounts import AccountIn, AccountOut, AccountUpdate

accounts_router = APIRouter()


@accounts_router.get("", response_model=list[AccountOut])
async def list_accounts(service: AccountServiceDep) -> list[AccountOut]:
    return await service.list()


@accounts_router.post("", response_model=AccountOut, status_code=201)
async def create_account(body: AccountIn, service: AccountServiceDep) -> AccountOut:
    return await service.create(body)


@accounts_router.patch("/{account_id}", response_model=AccountOut)
async def update_account(account_id: int, body: AccountUpdate, service: AccountServiceDep) -> AccountOut:
    return await service.update(account_id, body)
