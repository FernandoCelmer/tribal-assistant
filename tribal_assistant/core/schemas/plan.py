"""A village plan: ordered steps the specialists execute, written by the strategist."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

StepKind = Literal["build", "recruit", "unlock_scavenge"]
StepStatus = Literal["pending", "queued", "done", "blocked"]


class PlanStep(BaseModel):
    kind: StepKind
    target: str = Field(description="Building id (build), unit id (recruit) or scavenging tier 1-4 (unlock_scavenge).")
    amount: int = Field(ge=1, description="Level to reach (build), troops to have (recruit), 1 for unlock.")
    reason: str = ""
    status: StepStatus = "pending"
    note: str = ""


class VillagePlanOut(BaseModel):
    village_id: int
    village: str
    summary: str
    source: str
    refreshed_at: datetime | None
    steps: list[PlanStep]
    done: int
    total: int
