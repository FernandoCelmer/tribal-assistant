"""Input and output models for MCP tools that take or return lists or loose data."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from tribal_assistant.schemas.agents import AgentDecisionOut
from tribal_assistant.schemas.coordination import CoordinationOut
from tribal_assistant.schemas.farm import FarmTarget
from tribal_assistant.schemas.plan import VillagePlanOut
from tribal_assistant.schemas.world import NearbyVillage


class Decisions(BaseModel):
    decisions: list[AgentDecisionOut] = Field(description="Newest first: agent, action, arguments, ok, dry_run, reason and the game's answer.")


class Plans(BaseModel):
    plans: list[VillagePlanOut] = Field(description="One plan per village with each step's live status and progress.")


class Nearby(BaseModel):
    villages: list[NearbyVillage] = Field(description="Closest first, with travel minutes per unit.")


class FarmTargets(BaseModel):
    targets: list[FarmTarget] = Field(description="Local farm list the raider falls back on when world data is missing.")


class BarbarianTarget(BaseModel):
    coords: str = Field(description="Target coordinates x|y.")
    points: int | None = Field(default=None, description="Village points; high points on a former player village may mean troops left.")
    distance: float | None = Field(default=None, description="Distance in fields from the origin village.")
    minutes: dict[str, float] | None = Field(default=None, description="Travel minutes per unit.")
    recently_attacked: bool = Field(description="Hit recently; send_farm_attack will refuse it.")
    source: str = Field(default="world", description="world (public world data) or farm_targets (local list).")


class BarbarianTargets(BaseModel):
    targets: list[BarbarianTarget] = Field(description="Barbarian villages inside the attack radius, closest first.")
    note: str = Field(default="", description="Why the list is empty, when it is.")


class VillageState(BaseModel):
    village_id: int
    state: str = Field(description="Compact pt-BR summary: resources, queue, buildings, troops, scavenging, quests, plan, commands, goal.")


class Knowledge(BaseModel):
    model_config = ConfigDict(extra="allow")


class PlanStepIn(BaseModel):
    kind: Literal["build", "recruit", "unlock_scavenge"] = Field(description="build a level, recruit up to a troop total, or unlock a scavenging tier.")
    target: str = Field(description="Building id (build), unit id (recruit) or tier '1'-'4' (unlock_scavenge).")
    amount: int = Field(ge=1, le=50_000, description="Level to reach (build), troops to own in total (recruit), 1 for unlock_scavenge.")
    reason: str = Field(default="", max_length=200, description="Why this step, a few words.")


class ActionOutcome(BaseModel):
    ok: bool = Field(description="false when refused or failed; detail says why.")
    dry_run: bool = Field(description="true when nothing was sent to the game.")
    detail: str = Field(description="The game's answer, the simulation text, or 'RECUSADO: <reason>' from the guardrails.")
    data: dict[str, Any] = Field(default={}, description="Structured result: level, count, target, arrival, option_id...")


class SyncOutcome(BaseModel):
    ok: bool
    message: str


class Coordination(BaseModel):
    villages: list[CoordinationOut] = Field(description="Latest coordinator round per village: role, mode, next action, executed, deferred with reasons, reservations, vetoes and insights.")
