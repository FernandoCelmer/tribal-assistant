"""Writes the village plan the other specialists execute without AI."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.knowledge import GameKnowledge
from tribal_assistant.core.agents.plan import PlanTracker, RulePlanner
from tribal_assistant.core.agents.roles.base import VillageAgent
from tribal_assistant.core.schemas.agent_settings import AgentSettings

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox


class StrategistAgent(VillageAgent):
    key = "strategist"
    title = "Estrategista"
    mission = (
        "Escrever o plano da aldeia com set_village_plan: até 12 passos em ordem de prioridade que o "
        "especialistas de economia, infraestrutura e recrutamento seguem sozinhos, sem IA. Ordem de prioridade: 1) metas de missão "
        "próximas (dão recursos); 2) Armazém antes de um recurso passar de 85%; 3) Fazenda antes de a "
        "população passar de 85%; 4) minas equilibradas, a mais baixa primeiro; 5) Quartel 3 e tropas de "
        "saque (lanceiros, depois cavalaria leve com Estábulo 3); 6) coleta desbloqueada em ordem; "
        "7) caminho do primeiro nobre (Edifício principal 20, Ferreiro 20, Mercado 10, Academia). "
        "Passo build = nível a atingir (não +1, no máximo 3 níveis acima do atual); passo recruit = total "
        "de tropas a ter. Não inclua o que está feito ou bloqueado por requisito sem antes planejar o "
        "requisito. Respeite o objetivo da aldeia se houver. Use lookup_knowledge ou search_docs (ajuda, guias e tutoriais do fórum) só se tiver dúvida de "
        "requisito. Uma chamada set_village_plan basta; set_village_goal só se o objetivo mudar."
    )
    tools = ("lookup_knowledge", "search_docs", "read_doc", "set_village_plan", "set_village_goal")

    def system_prompt(self) -> str:
        return super().system_prompt() + "\n" + GameKnowledge.strategy

    def stale(self, ctx: VillageContext, config: AgentSettings) -> bool:
        if ctx.plan_refreshed_at is None:
            return True

        age = datetime.now(UTC).replace(tzinfo=None) - ctx.plan_refreshed_at
        return age > timedelta(minutes=config.plan_refresh_minutes)

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
