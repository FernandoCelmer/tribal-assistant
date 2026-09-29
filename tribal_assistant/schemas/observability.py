"""What the agents dashboard reads: rounds, traces, statistics, logs and village history."""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    trigger: str
    status: str
    brain: str
    provider: str | None
    model: str | None
    dry_run: bool
    started_at: datetime
    finished_at: datetime | None
    villages: int
    actions_ok: int
    actions_refused: int
    actions_failed: int
    tokens_in: int
    tokens_out: int
    error: str | None


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    village_id: int | None
    agent: str
    kind: str
    tool: str | None
    content: str
    is_error: bool
    created_at: datetime


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    village_id: int | None
    agent: str
    action: str
    arguments: dict[str, Any]
    ok: bool
    dry_run: bool
    reason: str
    result: str
    created_at: datetime

    @field_validator("arguments", mode="before")
    @classmethod
    def _parse(cls, value: Any) -> Any:
        return json.loads(value) if isinstance(value, str) else value


class RunDetailOut(BaseModel):
    run: RunOut
    villages: dict[int, str]
    steps: list[StepOut]
    decisions: list[DecisionOut]


class HourBucket(BaseModel):
    hour: datetime
    by_agent: dict[str, int]


class CountRow(BaseModel):
    label: str
    count: int


class AgentStat(BaseModel):
    agent: str
    actions: int
    ok: int
    refused: int
    failed: int
    last_action: str | None
    last_result: str | None
    last_at: datetime | None


class StatsOut(BaseModel):
    hours: int
    runs: int
    runs_failed: int
    actions_ok: int
    actions_refused: int
    actions_failed: int
    attacks: int
    builds: int
    recruits: int
    quests: int
    tokens_in: int
    tokens_out: int
    hourly: list[HourBucket]
    refusals: list[CountRow]
    by_action: list[CountRow]
    agents: list[AgentStat]


class FlowNode(BaseModel):
    id: str
    count: int


class FlowLink(BaseModel):
    source: str
    target: str
    count: int


class FlowOut(BaseModel):
    calls: int
    runs: int
    agents: list[FlowNode]
    tools: list[FlowNode]
    outcomes: list[FlowNode]
    agent_tool: list[FlowLink]
    tool_outcome: list[FlowLink]


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    at: datetime
    level: str
    source: str
    message: str
    process: str


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    village_id: int
    taken_at: datetime
    points: int
    wood: int
    clay: int
    iron: int
    storage: int
    pop_current: int
    pop_max: int
    troops_home: int
    troops_total: int


class LiveOut(BaseModel):
    running: bool
    run_id: str | None = None
    started_at: str | None = None
    village: str | None = None
    agent: str | None = None
    step: str | None = None
    next_run_at: datetime | None = None
    enabled: bool = False
