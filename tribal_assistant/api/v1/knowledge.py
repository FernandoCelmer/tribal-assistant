"""Game knowledge endpoints: buildings, units, base strategy and guides."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from tribal_assistant.core.services.knowledge import KnowledgeService

knowledge_router = APIRouter()
knowledge = KnowledgeService()


@knowledge_router.get("/strategy", response_class=PlainTextResponse)
async def strategy() -> str:
    return knowledge.strategy()


@knowledge_router.get("/buildings")
async def buildings() -> dict[str, Any]:
    return knowledge.buildings()


@knowledge_router.get("/buildings/{key}")
async def building(key: str) -> dict[str, Any]:
    return knowledge.building(key)


@knowledge_router.get("/units")
async def units() -> dict[str, Any]:
    return knowledge.units()


@knowledge_router.get("/units/{key}")
async def unit(key: str) -> dict[str, Any]:
    return knowledge.unit(key)


@knowledge_router.get("/guides/{name}", response_class=PlainTextResponse)
async def guide(name: str) -> str:
    return knowledge.guide(name)
