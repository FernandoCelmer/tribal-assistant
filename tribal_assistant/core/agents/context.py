"""The village snapshot every agent reads: compact, JSON-ready, with live resource estimates."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from tribal_assistant.core.agents.coordination.policy import Policy
from tribal_assistant.core.schemas.game import VillageOverview
from tribal_assistant.core.schemas.plan import PlanStep


@dataclass
class VillageContext:
    village: VillageOverview
    player: dict[str, Any] | None
    commands: list[dict[str, Any]]
    quests: list[dict[str, Any]]
    rewards_pending: int
    goal: str | None
    recent: list[dict[str, Any]]
    stock: dict[str, int] = field(default_factory=dict)
    pop_free: int = 0
    plan: list[PlanStep] = field(default_factory=list)
    plan_summary: str = ""
    plan_refreshed_at: datetime | None = None
    goal_set_at: datetime | None = None
    lessons: str = ""
    coordination: str = ""
    policy: Policy = field(default_factory=Policy)

    @property
    def id(self) -> int:
        return self.village.id

    @property
    def game_id(self) -> str:
        return self.village.game_id or ""

    @property
    def queue(self) -> list[dict[str, Any]]:
        return [
            {"building": b.name, "level": b.queued_level, "until": b.queued_until}
            for b in self.village.buildings
            if b.queued_level
        ]

    @property
    def levels(self) -> dict[str, int]:
        return {b.name: b.level for b in self.village.buildings}

    def building(self, name: str) -> Any:
        return next((b for b in self.village.buildings if b.name == name), None)

    def unit(self, name: str) -> Any:
        return next((u for u in self.village.units if u.name == name), None)

    def spend(self, wood: int = 0, clay: int = 0, iron: int = 0, pop: int = 0) -> None:
        self.stock["wood"] -= wood
        self.stock["clay"] -= clay
        self.stock["iron"] -= iron
        self.pop_free -= pop
