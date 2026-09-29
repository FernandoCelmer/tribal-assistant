"""Writes the village plan the other specialists execute without AI."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from tribal_assistant.agents.context import VillageContext
from tribal_assistant.agents.knowledge import GameKnowledge
from tribal_assistant.agents.plan import PlanTracker, RulePlanner
from tribal_assistant.agents.roles.base import VillageAgent
from tribal_assistant.schemas.agent_settings import AgentSettings

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox


class StrategistAgent(VillageAgent):
    key = "strategist"
    title = "Estrategista"
    mission = (
        "Escrever o plano da aldeia com set_village_plan: até 12 passos em ordem de prioridade que os "
        "outros agentes executam sozinhos. Equilibre: metas de missão (dão recursos), armazém antes de "
        "encher, fazenda antes de a população travar, produção equilibrada, quartel e tropas de saque, "
        "coleta desbloqueada, e o caminho do primeiro nobre (Edifício principal 20, Ferreiro 20, Mercado "
        "10, Academia). Use lookup_knowledge só se tiver dúvida de requisito."
    )
    tools = ("lookup_knowledge", "set_village_plan", "set_village_goal")

    def system_prompt(self) -> str:
        return super().system_prompt() + "\n" + GameKnowledge.strategy

    def stale(self, ctx: VillageContext, config: AgentSettings) -> bool:
        if ctx.plan_refreshed_at is None:
            return True

        age = datetime.now(UTC).replace(tzinfo=None) - ctx.plan_refreshed_at
        return age > timedelta(hours=config.plan_refresh_hours)

    def needs_llm(self, ctx: VillageContext, config: AgentSettings) -> bool:
        return self.stale(ctx, config) or PlanTracker.needs_refresh(ctx.plan)

    async def rules(self, box: "Toolbox") -> str:
        ctx = box.ctx
        done = sum(1 for s in ctx.plan if s.status == "done")

        if not self.needs_llm(ctx, box.config):
            return f"plano mantido: {done}/{len(ctx.plan)} passos feitos"

        summary, steps = RulePlanner().plan(ctx)
        outcome = await box.invoke(
            "set_village_plan",
            {"summary": summary, "steps": [s.model_dump(include={"kind", "target", "amount", "reason"}) for s in steps]},
        )
        return outcome.text
