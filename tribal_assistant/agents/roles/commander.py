"""Military: the plan's military builds and recruitment, plus spending surplus on troops."""

from typing import TYPE_CHECKING

from tribal_assistant.agents.context import VillageContext
from tribal_assistant.agents.plan import PlanTracker
from tribal_assistant.agents.roles.base import VillageAgent
from tribal_assistant.schemas.agent_settings import AgentSettings

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox

FARM_UNITS = ("light", "spear", "axe")
BATCH = 25


class CommanderAgent(VillageAgent):
    key = "commander"
    title = "Comandante"
    mission = (
        "Executar as obras militares e o recrutamento do plano. Prioridades: 1) próximo passo militar "
        "pendente do plano (quartel, estábulo, ferreiro, muralha, academia); 2) recrutar o que falta para "
        "o total de tropas do plano, em lotes de até 25; 3) com o armazém acima de 85%, transformar o "
        "excedente em tropas de saque (cavalaria leve, senão lanceiros, senão bárbaros). Não recrute "
        "unidade que o plano não pede fora do caso de excedente, e não construa fora da sua área."
    )
    tools = ("get_village_state", "upgrade_building", "recruit_units")
    buildings = ("barracks", "stable", "garage", "smith", "wall", "statue", "snob", "watchtower", "place")

    def needs_llm(self, ctx: VillageContext, config: AgentSettings) -> bool:
        return False

    async def rules(self, box: "Toolbox") -> str:
        ctx = box.ctx
        notes = []

        planned = [b for b in PlanTracker.next_builds(ctx.plan) if b in self.buildings]
        built = await self.build_first_affordable(box, planned, limit=self.free_slots(box), reason="passo do plano")
        if built:
            notes.append(f"plano: {', '.join(built)}")

        for step in PlanTracker.next_recruits(ctx.plan):
            unit = ctx.unit(step.target)
            if unit is None:
                continue

            missing = step.amount - unit.total - sum(r.count for r in ctx.village.recruit_orders if r.unit == step.target)
            plan = box.guard.plan_recruit(ctx, step.target, min(BATCH, max(0, missing)))
            if plan.refusal:
                continue

            outcome = await box.invoke("recruit_units", {"unit": step.target, "count": plan.count, "reason": "passo do plano"})
            notes.append(outcome.text)
            break

        if not notes and self.near_full(ctx):
            for unit in FARM_UNITS:
                plan = box.guard.plan_recruit(ctx, unit, BATCH)
                if plan.refusal:
                    continue

                outcome = await box.invoke("recruit_units", {"unit": unit, "count": plan.count, "reason": "armazém quase cheio: usar recursos"})
                notes.append(outcome.text)
                break

        return "; ".join(notes) or "nada a recrutar ou construir agora"
