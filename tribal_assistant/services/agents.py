"""Village agents: run a round, read decisions, quests and configuration."""

import json
from dataclasses import asdict

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.agents.runner import AgentRunner
from tribal_assistant.db.session import get_session
from tribal_assistant.repositories.agent_settings import AgentSettingsRepository
from tribal_assistant.repositories.agents import AgentRepository
from tribal_assistant.schemas.agent_settings import AgentSettings, AgentSettingsUpdate
from tribal_assistant.schemas.agents import (
    AgentConfigOut,
    AgentDecisionOut,
    AgentRunOut,
    QuestOut,
    QuestRewardOut,
    QuestsOut,
)
from tribal_assistant.schemas.plan import VillagePlanOut


class AgentService:
    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        self.repository = AgentRepository(session)
        self.settings_repository = AgentSettingsRepository(session)

    async def run(self, dry_run: bool | None = None, village_ids: list[int] | None = None) -> AgentRunOut:
        report = await AgentRunner(dry_run=dry_run, trigger="dashboard").run(village_ids)
        return AgentRunOut.model_validate(asdict(report))

    async def decisions(self, village_id: int | None = None, limit: int = 50) -> list[AgentDecisionOut]:
        rows = await self.repository.decisions(village_id=village_id, limit=limit)
        return [AgentDecisionOut.model_validate(row) for row in rows]

    async def quests(self) -> QuestsOut:
        return QuestsOut(
            quests=[
                QuestOut(
                    quest_id=q.quest_id,
                    line_id=q.line_id,
                    title=q.title,
                    state=q.state,
                    description=q.description,
                    goals=json.loads(q.goals),
                    can_complete=q.can_complete,
                )
                for q in await self.repository.quests()
            ],
            rewards=[
                QuestRewardOut(reward_id=r.reward_id, label=r.label)
                for r in await self.repository.pending_rewards()
            ],
        )

    async def plans(self) -> list[VillagePlanOut]:
        from tribal_assistant.agents.context import ContextLoader

        contexts = await ContextLoader(self.repository.session).load()
        return [
            VillagePlanOut(
                village_id=ctx.id,
                village=f"{ctx.village.name} ({ctx.village.coords})",
                summary=ctx.plan_summary,
                source=(await self._plan_source(ctx.id)),
                refreshed_at=ctx.plan_refreshed_at,
                steps=ctx.plan,
                done=sum(1 for s in ctx.plan if s.status == "done"),
                total=len(ctx.plan),
            )
            for ctx in contexts
        ]

    async def _plan_source(self, village_id: int) -> str:
        from tribal_assistant.repositories.plans import PlanRepository

        row = await PlanRepository(self.repository.session).get(village_id)
        return row.source if row else "nenhum"

    async def settings(self) -> AgentSettings:
        return await self.settings_repository.get()

    async def update_settings(self, patch: AgentSettingsUpdate) -> AgentSettings:
        return await self.settings_repository.update(patch)

    async def config(self) -> AgentConfigOut:
        runner = AgentRunner()
        llm = getattr(runner.brain, "llm", None)

        return AgentConfigOut(
            brain=runner.brain.name,
            provider=llm.provider if llm else "none",
            model=llm.model if llm else None,
            agents=[
                {"key": a.key, "title": a.title, "tools": list(a.tools), "buildings": list(a.buildings)}
                for a in runner.agents
            ],
            settings=await self.settings_repository.get(),
            last_run_at=await self.settings_repository.last_run_at(),
        )
