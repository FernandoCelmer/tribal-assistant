"""Aggregate every v1 router here."""

from fastapi import APIRouter

from app.api.v1.bot import bot_router
from app.api.v1.farm import farm_router
from app.api.v1.villages import villages_router

v1_router = APIRouter()
v1_router.include_router(villages_router, prefix="/villages", tags=["Villages"])
v1_router.include_router(farm_router, prefix="/farm", tags=["Farm"])
v1_router.include_router(bot_router, prefix="/bot", tags=["Bot"])
