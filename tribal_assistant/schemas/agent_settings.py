"""Agent settings edited at runtime (dashboard, API, CLI, MCP) and stored in the database."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentSettings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    enabled: bool = Field(default=False, description="Run the agents on a schedule inside the server.")
    interval_minutes: int = Field(default=10, ge=1, le=1440, description="Minutes between scheduled rounds.")
    dry_run: bool = Field(default=False, description="Simulate and log without acting in the game.")
    resource_reserve: float = Field(default=0.1, ge=0, le=0.9, description="Share of storage always kept untouched by recruiting.")
    recruit_budget: float = Field(default=0.5, ge=0, le=1, description="Share of spare resources recruiting may spend per round.")
    max_attacks_per_hour: int = Field(default=12, ge=0, le=200, description="Attacks per village per hour.")
    attack_radius: int = Field(default=12, ge=1, le=50, description="Maximum distance to a barbarian target, in fields.")
    retarget_minutes: int = Field(default=30, ge=0, le=1440, description="Minutes before the same target may be hit again.")
    build_queue_slots: int = Field(default=2, ge=1, le=5, description="Build orders the agents may keep queued per village.")
    auto_finish_free: bool = Field(default=True, description="Click the free finish-now button on short builds (never paid ones).")
    llm_agents: list[str] = Field(default_factory=lambda: ["strategist"], description="Agents that may call the AI; the rest run on rules.")
    plan_refresh_minutes: int = Field(default=360, ge=5, le=10080, description="Minutes before the strategist rewrites the plan.")
    llm_max_steps: int = Field(default=6, ge=1, le=20, description="Tool rounds per AI conversation.")
    approval_actions: list[str] = Field(default_factory=list, description="Actions the coordinator only proposes and waits for approval.")

    @model_validator(mode="before")
    @classmethod
    def _hours_to_minutes(cls, data: Any) -> Any:
        if isinstance(data, dict) and "plan_refresh_hours" in data:
            data = dict(data)
            hours = data.pop("plan_refresh_hours")
            data["plan_refresh_minutes"] = int(hours) * 60

        return data


class AgentSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    dry_run: bool | None = None
    resource_reserve: float | None = Field(default=None, ge=0, le=0.9)
    recruit_budget: float | None = Field(default=None, ge=0, le=1)
    max_attacks_per_hour: int | None = Field(default=None, ge=0, le=200)
    attack_radius: int | None = Field(default=None, ge=1, le=50)
    retarget_minutes: int | None = Field(default=None, ge=0, le=1440)
    build_queue_slots: int | None = Field(default=None, ge=1, le=5)
    auto_finish_free: bool | None = None
    llm_agents: list[str] | None = None
    plan_refresh_minutes: int | None = Field(default=None, ge=5, le=10080)
    llm_max_steps: int | None = Field(default=None, ge=1, le=20)
    approval_actions: list[str] | None = None
