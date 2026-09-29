import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from tribal_assistant.schemas.agent_settings import AgentSettings


class AgentDecisionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    run_id: str
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


class QuestGoalOut(BaseModel):
    title: str
    text: str
    current: int | None
    target: int | None


class QuestOut(BaseModel):
    quest_id: str
    line_id: str
    title: str
    state: str
    description: str
    goals: list[QuestGoalOut]
    can_complete: bool


class QuestRewardOut(BaseModel):
    reward_id: str
    label: str


class QuestsOut(BaseModel):
    quests: list[QuestOut]
    rewards: list[QuestRewardOut]


class AgentRunRequest(BaseModel):
    dry_run: bool | None = None
    village_ids: list[int] | None = None


class VillageRunOut(BaseModel):
    village: str
    summaries: dict[str, str]


class AgentRunOut(BaseModel):
    run_id: str
    brain: str
    dry_run: bool
    villages: list[VillageRunOut] = Field(default_factory=list)
    error: str | None = None


class AgentConfigOut(BaseModel):
    brain: str
    provider: str
    model: str | None
    agents: list[dict[str, Any]]
    settings: AgentSettings
    last_run_at: datetime | None
