"""The village snapshot every agent reads: compact, JSON-ready, with live resource estimates."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.agents.knowledge import GameKnowledge
from tribal_assistant.repositories.agents import AgentRepository
from tribal_assistant.repositories.plans import PlanRepository
from tribal_assistant.schemas.game import GameOverview, VillageOverview
from tribal_assistant.schemas.plan import PlanStep
from tribal_assistant.services.game import GameService


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

    def to_prompt(self, queue_slots: int) -> dict[str, Any]:
        v = self.village
        slots = max(0, queue_slots - len(self.queue))

        return {
            "village": {"id": v.id, "name": v.name, "coords": v.coords, "points": v.points},
            "resources": {
                **self.stock,
                "storage": v.storage,
                "production_per_hour": {"wood": v.wood_prod, "clay": v.clay_prod, "iron": v.iron_prod},
                "population": {"used": v.pop_current, "max": v.pop_max, "free": self.pop_free},
            },
            "build_queue": self.queue,
            "build_slots_free": slots,
            "buildings": [
                {
                    "id": b.name,
                    "label": b.label,
                    "level": b.level,
                    "max": b.max_level,
                    "next_cost": {"wood": b.next_wood, "clay": b.next_clay, "iron": b.next_iron, "pop": b.next_pop},
                    "build_seconds": b.build_time,
                    "can_build": b.can_build,
                    "blocker": b.blocker,
                    "missing_requirements": GameKnowledge.missing_requirements(b.name, self.levels),
                }
                for b in v.buildings
            ],
            "units": [
                {
                    "id": u.name,
                    "home": u.home,
                    "away": u.away,
                    "can_recruit": u.available,
                    "max_recruit": u.max_recruit,
                    "cost": {"wood": u.cost_wood, "clay": u.cost_clay, "iron": u.cost_iron, "pop": u.cost_pop},
                    "blocker": u.blocker,
                }
                for u in v.units
            ],
            "recruiting": [r.model_dump(mode="json") for r in v.recruit_orders],
            "commands": self.commands,
            "scavenge": [s.model_dump(mode="json") for s in v.scavenge],
            "advisor": [r.model_dump(mode="json") for r in v.recommendations],
            "quests": self.quests,
            "quest_rewards_pending": self.rewards_pending,
            "player": self.player,
            "goal": self.goal,
            "recent_decisions": self.recent,
        }


class ContextLoader:
    """Builds one VillageContext per own village from the synced database state."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AgentRepository(session)
        self.plans = PlanRepository(session)

    async def load(self, village_ids: list[int] | None = None) -> list[VillageContext]:
        overview: GameOverview = await GameService(self.session).overview()
        quests = await self._quests()
        rewards = len(await self.repo.pending_rewards())
        player = overview.player.model_dump(mode="json") if overview.player else None

        contexts = []
        for village in overview.villages:
            if village_ids and village.id not in village_ids:
                continue

            contexts.append(
                VillageContext(
                    village=village,
                    player=player,
                    commands=[
                        c.model_dump(mode="json")
                        for c in overview.commands
                        if c.village_coords == village.coords
                    ],
                    quests=quests,
                    rewards_pending=rewards,
                    goal=await self.repo.goal(village.id),
                    recent=await self._recent(village.id),
                    stock=self._live_stock(village),
                    pop_free=village.pop_max - village.pop_current,
                )
            )
            await self._attach_plan(contexts[-1])

        return contexts

    async def _attach_plan(self, ctx: VillageContext) -> None:
        from tribal_assistant.agents.plan import PlanTracker

        row = await self.plans.get(ctx.id)
        ctx.plan = PlanTracker().evaluate(ctx, PlanRepository.steps(row))
        ctx.plan_summary = row.summary if row else ""
        ctx.plan_refreshed_at = row.refreshed_at if row else None

    async def _quests(self) -> list[dict[str, Any]]:
        return [
            {
                "id": q.quest_id,
                "title": q.title,
                "state": q.state,
                "goals": json.loads(q.goals),
                "can_complete": q.can_complete,
            }
            for q in await self.repo.quests()
        ]

    async def _recent(self, village_id: int) -> list[dict[str, Any]]:
        return [
            {
                "at": d.created_at.isoformat(timespec="minutes"),
                "agent": d.agent,
                "action": d.action,
                "ok": d.ok,
                "result": d.result[:160],
            }
            for d in await self.repo.decisions(village_id=village_id, limit=10)
        ]

    @staticmethod
    def _live_stock(village: VillageOverview) -> dict[str, int]:
        elapsed = 0.0
        if village.synced_at:
            elapsed = max(0.0, (datetime.now(UTC) - village.synced_at).total_seconds() / 3600)

        return {
            key: min(village.storage, int(getattr(village, key) + getattr(village, f"{key}_prod") * elapsed))
            for key in ("wood", "clay", "iron")
        }
