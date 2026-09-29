"""Aggregate every v1 router here."""

from fastapi import APIRouter, Depends

from tribal_assistant.api.v1.accounts import accounts_router
from tribal_assistant.api.v1.agents import agents_router
from tribal_assistant.api.v1.assistant import assistant_router
from tribal_assistant.api.v1.farm import farm_router
from tribal_assistant.api.v1.game import game_router
from tribal_assistant.api.v1.observability import observability_router
from tribal_assistant.api.v1.system import system_router
from tribal_assistant.api.v1.villages import villages_router
from tribal_assistant.api.v1.world import world_router
from tribal_assistant.db.session import get_session

v1_router = APIRouter(dependencies=[Depends(get_session)])
v1_router.include_router(accounts_router, prefix="/accounts", tags=["Accounts"])
v1_router.include_router(villages_router, prefix="/villages", tags=["Villages"])
v1_router.include_router(farm_router, prefix="/farm", tags=["Farm"])
v1_router.include_router(assistant_router, prefix="/assistant", tags=["Assistant"])
v1_router.include_router(game_router, prefix="/game", tags=["Game"])
v1_router.include_router(world_router, prefix="/world", tags=["World"])
v1_router.include_router(observability_router, tags=["Observability"])
v1_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
v1_router.include_router(system_router, prefix="/system", tags=["System"])
