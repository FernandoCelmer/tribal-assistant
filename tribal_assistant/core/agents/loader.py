"""Builds the village snapshots from the synced database state."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.absence import Absence
from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.policy import Policy
from tribal_assistant.core.agents.knobs import KnobStore
from tribal_assistant.core.agents.learning import LessonBook
from tribal_assistant.core.agents.plan import PlanTracker
from tribal_assistant.core.agents.sightings import SightingBook
from tribal_assistant.core.repositories.agents import AgentRepository
from tribal_assistant.core.repositories.coordination import CoordinationRepository
from tribal_assistant.core.repositories.plans import PlanRepository
from tribal_assistant.core.schemas.game import GameOverview, VillageOverview
from tribal_assistant.core.services.game import GameService


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
                    goal_set_at=await self.repo.goal_set_at(village.id),
                    recent=await self._recent(village.id),
                    stock=self._live_stock(village),
                    pop_free=village.pop_max - village.pop_current,
                )
            )
            await self._attach_plan(contexts[-1])

        return contexts

    async def _attach_plan(self, ctx: VillageContext) -> None:
        row = await self.plans.get(ctx.id)
        ctx.plan = PlanTracker().evaluate(ctx, PlanRepository.steps(row))
        ctx.plan_summary = row.summary if row else ""
        ctx.plan_refreshed_at = row.refreshed_at if row else None

        ctx.lessons = await LessonBook(self.plans.session).summary()
        ctx.coordination = await self._coordination(ctx.id)
        ctx.sightings = await SightingBook(self.plans.session).summary()

        strategy = await CoordinationRepository(self.plans.session).strategy(ctx.id)
        ctx.policy = Policy.for_role(strategy.role if strategy else "growth", await KnobStore(self.plans.session).load())
        await Absence(self.plans.session).attach(ctx)

    async def _coordination(self, village_id: int) -> str:
        rows = await CoordinationRepository(self.plans.session).history(village_id, 1)
        if not rows:
            return ""

        data = json.loads(rows[0].data or "{}")
        deferred = "; ".join(f"{d['title']} ({d['why']})" for d in data.get("deferred", [])[:3])
        reserved = ", ".join(r["purpose"] for r in data.get("budget", {}).get("reservations", []))
        return (
            f"Coordenador: papel {data.get('role')}, modo {data.get('mode')}"
            + (f"; reservas: {reserved}" if reserved else "")
            + (f"; adiadas: {deferred}" if deferred else "")
        )

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
