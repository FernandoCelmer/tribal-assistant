"""Aggregate every v1 router here."""

from fastapi import APIRouter

from app.api.v1.assistant import assistant_router
from app.api.v1.farm import farm_router
from app.api.v1.game import game_router
from app.api.v1.villages import villages_router
from app.api.v1.world import world_router

v1_router = APIRouter()
v1_router.include_router(villages_router, prefix="/villages", tags=["Villages"])
v1_router.include_router(farm_router, prefix="/farm", tags=["Farm"])
v1_router.include_router(assistant_router, prefix="/assistant", tags=["Assistant"])
v1_router.include_router(game_router, prefix="/game", tags=["Game"])
v1_router.include_router(world_router, prefix="/world", tags=["World"])
