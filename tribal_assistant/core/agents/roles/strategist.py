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
        "Escrever o plano da aldeia com set_village_plan: até 12 passos em ordem de prioridade que os "
        "especialistas de economia, infraestrutura e recrutamento seguem sozinhos, sem IA. Ordem de prioridade: "
        "1) Estátua 1 logo depois do Quartel 1 (paladino saqueia cedo); 2) metas de missão próximas, inclusive "
        "Muralha 1 (devolve 300 de cada) e Esconderijo 3 (dá 100), nunca acima do nível 3 por missão, e nunca a "
        "missão da milícia (não ative a milícia); 3) Armazém antes de um recurso passar de 85%; 4) Fazenda antes "
        "de a população passar de 85%; 5) minas com madeira sempre a mais alta e ferro 3 níveis abaixo de "
        "madeira e argila até existir Estábulo; 6) lanceiros até 40 (missão), depois o portão da cavalaria "
        "leve: Edifício principal 10 (não passe de 10 antes do Estábulo 3), Quartel 5, Ferreiro 5, Estábulo 3, "
        "Armazém 6-7 para caber os custos; 7) coleta desbloqueada em ordem; 8) fim da proteção: nas 72h finais "
        "Muralha 8 e cerca de 80 lanceiros + 80 espadachins; machados (bárbaros) só ~12h antes do fim; "
        "9) depois da proteção, a cada 3 níveis de EP, 2 de Quartel e 2 de Estábulo; 10) nobre só com "
        "Edifício principal 20, Ferreiro 20, Mercado 10, Fazenda 24 e exército de verdade. "
        "Passo build = nível a atingir (não +1, no máximo 3 níveis acima do atual); passo recruit = total "
        "de tropas a ter. Não inclua o que está feito ou bloqueado por requisito sem antes planejar o "
        "requisito. Respeite o objetivo da aldeia se houver. A cada mudança de fase (início, portão do estábulo, "
        "fim da proteção, academia) chame search_docs antes de planejar, por exemplo \"sprint popeye\", "
        "\"fim da proteção\", \"muralha cavalaria leve bárbara\", \"academia armazenamento\" ou "
        "\"torre de vigia\"; fora disso use lookup_knowledge ou search_docs só com dúvida de requisito. "
        "Uma chamada set_village_plan basta; set_village_goal só se o objetivo mudar."
    )
    tools = ("lookup_knowledge", "search_docs", "read_doc", "get_forecast", "get_incoming", "simulate_battle", "get_target_intel", "set_village_plan", "set_village_goal")

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
