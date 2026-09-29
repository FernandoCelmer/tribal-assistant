"""Village agent endpoints."""

from fastapi import APIRouter, Depends, Query

from tribal_assistant.core.schemas.agent_settings import AgentSettings, AgentSettingsUpdate
from tribal_assistant.core.schemas.agents import (
    AgentActOut,
    AgentActRequest,
    AgentConfigOut,
    AgentDecisionOut,
    AgentRunOut,
    AgentRunRequest,
    LessonOut,
    QuestsOut,
)
from tribal_assistant.core.schemas.coordination import CoordinationOut, ProposerOut, RoleIn, RoleOut
from tribal_assistant.core.schemas.plan import VillagePlanOut
from tribal_assistant.core.services.agents import AgentService

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


@agents_router.post("/act", response_model=AgentActOut)
async def act(body: AgentActRequest, service: AgentService = Depends(AgentService)) -> AgentActOut:
    return await service.act(body)


@agents_router.get("/lessons", response_model=list[LessonOut])
async def lessons(
    topic: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    service: AgentService = Depends(AgentService),
) -> list[LessonOut]:
    return await service.lessons(topic, limit)


@agents_router.get("/coordination", response_model=list[CoordinationOut])
async def coordination(service: AgentService = Depends(AgentService)) -> list[CoordinationOut]:
    return await service.coordination()


@agents_router.get("/coordination/{village_id}", response_model=list[CoordinationOut])
async def coordination_history(
    village_id: int,
    limit: int = Query(default=20, ge=1, le=200),
    service: AgentService = Depends(AgentService),
) -> list[CoordinationOut]:
    return await service.coordination_history(village_id, limit)


@agents_router.put("/villages/{village_id}/role", response_model=RoleOut)
async def set_role(village_id: int, body: RoleIn, service: AgentService = Depends(AgentService)) -> RoleOut:
    return await service.set_role(village_id, body)


@agents_router.get("/proposers", response_model=list[ProposerOut])
async def proposers() -> list[ProposerOut]:
    return AgentService.proposers()
