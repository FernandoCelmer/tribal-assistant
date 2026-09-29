"""Village agents: run a round, read decisions, quests and configuration."""

import json
from dataclasses import asdict
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import ContextLoader
from tribal_assistant.core.agents.roles.operator import OperatorAgent
from tribal_assistant.core.agents.runner import AgentRunner
from tribal_assistant.core.agents.toolbox import Toolbox
from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.core.repositories.agent_settings import AgentSettingsRepository
from tribal_assistant.core.repositories.agents import AgentRepository
from tribal_assistant.core.repositories.coordination import CoordinationRepository
from tribal_assistant.core.repositories.lessons import LessonRepository
from tribal_assistant.core.schemas.agent_settings import AgentSettings, AgentSettingsUpdate
from tribal_assistant.core.schemas.agents import (
    AgentActOut,
    AgentActRequest,
    AgentConfigOut,
    AgentDecisionOut,
    AgentRunOut,
    LessonOut,
    QuestOut,
    QuestRewardOut,
    QuestsOut,
)
from tribal_assistant.core.schemas.coordination import CoordinationOut, ProposerOut, RoleIn, RoleOut
from tribal_assistant.core.schemas.plan import VillagePlanOut


class AgentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AgentRepository(session)
        self.settings_repository = AgentSettingsRepository(session)

    async def run(self, dry_run: bool | None = None, village_ids: list[int] | None = None) -> AgentRunOut:
        report = await AgentRunner(dry_run=dry_run, trigger="dashboard").run(village_ids)
        return AgentRunOut.model_validate(asdict(report))

    async def act(self, request: AgentActRequest) -> AgentActOut:
        contexts = await ContextLoader(self.session).load([request.village_id])
        if not contexts:
            raise NotFoundError(f"aldeia {request.village_id} não sincronizada")

        box = Toolbox(
            agent=OperatorAgent(),
            ctx=contexts[0],
            session=self.session,
            config=await self.settings_repository.get(),
            run_id=f"{request.source}-{uuid4().hex[:8]}",
            dry_run=request.dry_run,
        )
        outcome = await box.invoke(request.tool, request.arguments)

        return AgentActOut(ok=outcome.ok, dry_run=request.dry_run, detail=outcome.text, data=outcome.data)

    async def coordination(self) -> list[CoordinationOut]:
        repo = CoordinationRepository(self.session)
        names = {v.id: f"{v.name} ({v.coords})" for v in await self._own_villages()}
        items = []
        for row in await repo.latest():
            strategy = await repo.strategy(row.village_id)
            out = CoordinationOut.model_validate(row)
            out.village = names.get(row.village_id, str(row.village_id))
            out.manual_role = bool(strategy and strategy.manual)
            items.append(out)

        return sorted(items, key=lambda o: o.village_id)

    async def set_role(self, village_id: int, body: RoleIn) -> RoleOut:
        from tribal_assistant.core.agents.coordination.roles import RoleSelector

        repo = CoordinationRepository(self.session)
        if body.role is None:
            contexts = await ContextLoader(self.session).load([village_id])
            if not contexts:
                raise NotFoundError(f"aldeia {village_id} não sincronizada")

            role, reason = await RoleSelector(self.session).evaluate(contexts[0])
            row = await repo.set_strategy(village_id, role.value, reason, manual=False)
        else:
            row = await repo.set_strategy(village_id, body.role, body.reason or "definido no painel", manual=True)

        return RoleOut(village_id=row.village_id, role=row.role, manual=row.manual, reason=row.reason)

    @staticmethod
    def proposers() -> list[ProposerOut]:
        from tribal_assistant.core.agents.coordination.round import VillageRound

        return [ProposerOut(**item) for item in VillageRound.describe()]

    async def _own_villages(self):
        from sqlalchemy import select

        from tribal_assistant.core.models.village import Village

        return (await self.session.execute(select(Village).where(Village.is_own.is_(True)))).scalars().all()

    async def lessons(self, topic: str | None = None, limit: int = 100) -> list[LessonOut]:
        rows = await LessonRepository(self.session).list(topic, limit)
        return [LessonOut.model_validate(row) for row in rows]

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
        from tribal_assistant.core.agents.context import ContextLoader

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
        from tribal_assistant.core.repositories.plans import PlanRepository

        row = await PlanRepository(self.repository.session).get(village_id)
        return row.source if row else "nenhum"

    async def settings(self) -> AgentSettings:
        return await self.settings_repository.get()

    async def update_settings(self, patch: AgentSettingsUpdate) -> AgentSettings:
        return await self.settings_repository.update(patch)

    async def config(self) -> AgentConfigOut:
        from tribal_assistant.core.agents.coordination.round import VillageRound

        runner = AgentRunner()
        llm = getattr(runner.brain, "llm", None)

        return AgentConfigOut(
            brain=runner.brain.name,
            provider=llm.provider if llm else "none",
            model=llm.model if llm else None,
            agents=[
                *({"key": a.key, "title": a.title, "tools": list(a.tools), "buildings": list(a.buildings)} for a in runner.agents),
                *({"key": p["key"], "title": p["title"], "tools": [], "buildings": [], "delivers": p["delivers"]} for p in VillageRound.describe()),
            ],
            settings=await self.settings_repository.get(),
            last_run_at=await self.settings_repository.last_run_at(),
        )
