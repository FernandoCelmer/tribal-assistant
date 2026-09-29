"""Output models for MCP tools that return lists or loose data."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from tribal_assistant.schemas.agents import AgentDecisionOut
from tribal_assistant.schemas.farm import FarmTarget
from tribal_assistant.schemas.plan import VillagePlanOut
from tribal_assistant.schemas.world import NearbyVillage


class Decisions(BaseModel):
    decisions: list[AgentDecisionOut]


class Plans(BaseModel):
    plans: list[VillagePlanOut]


class Nearby(BaseModel):
    villages: list[NearbyVillage]


class FarmTargets(BaseModel):
    targets: list[FarmTarget]


class Knowledge(BaseModel):
    model_config = ConfigDict(extra="allow")


class ActionOutcome(BaseModel):
    ok: bool
    dry_run: bool
    detail: str
    data: dict[str, Any] = {}


class SyncOutcome(BaseModel):
    ok: bool
    message: str
