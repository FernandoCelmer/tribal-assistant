"""Village agent endpoints."""

from fastapi import APIRouter, Depends, Query

from tribal_assistant.schemas.agent_settings import AgentSettings, AgentSettingsUpdate
from tribal_assistant.schemas.agents import (
    AgentConfigOut,
    AgentDecisionOut,
    AgentRunOut,
    AgentRunRequest,
    QuestsOut,
)
from tribal_assistant.schemas.plan import VillagePlanOut
from tribal_assistant.services.agents import AgentService

agents_router = APIRouter()


@agents_router.get("/config", response_model=AgentConfigOut)
async def config(service: AgentService = Depends(AgentService)) -> AgentConfigOut:
    return await service.config()


@agents_router.get("/plans", response_model=list[VillagePlanOut])
async def plans(service: AgentService = Depends(AgentService)) -> list[VillagePlanOut]:
    return await service.plans()


@agents_router.get("/settings", response_model=AgentSettings)
async def get_settings(service: AgentService = Depends(AgentService)) -> AgentSettings:
    return await service.settings()


@agents_router.patch("/settings", response_model=AgentSettings)
async def update_settings(
    body: AgentSettingsUpdate, service: AgentService = Depends(AgentService)
) -> AgentSettings:
    return await service.update_settings(body)


@agents_router.get("/decisions", response_model=list[AgentDecisionOut])
async def decisions(
    village_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    service: AgentService = Depends(AgentService),
) -> list[AgentDecisionOut]:
    return await service.decisions(village_id, limit)


@agents_router.get("/quests", response_model=QuestsOut)
async def quests(service: AgentService = Depends(AgentService)) -> QuestsOut:
    return await service.quests()


@agents_router.post("/run", response_model=AgentRunOut)
async def run(body: AgentRunRequest, service: AgentService = Depends(AgentService)) -> AgentRunOut:
    return await service.run(body.dry_run, body.village_ids)
