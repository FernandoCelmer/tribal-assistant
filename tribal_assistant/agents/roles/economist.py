"""Economy: executes the plan's builds, unlocks scavenging, spends resources before storage fills."""

from typing import TYPE_CHECKING

from tribal_assistant.agents.context import VillageContext
from tribal_assistant.agents.plan import PlanTracker
from tribal_assistant.agents.roles.base import VillageAgent
from tribal_assistant.schemas.agent_settings import AgentSettings

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox


class EconomistAgent(VillageAgent):
    key = "economist"
    title = "Economista"
    mission = (
        "Executar as obras econômicas do plano na ordem e não deixar recurso parado. Prioridades: "
        "1) passos de construção pendentes do plano, do primeiro ao último, enquanto houver vaga na fila; "
        "2) desbloquear o próximo nível de coleta pedido pelo plano; 3) com o armazém acima de 85% e vaga "
        "livre, subir o que o conselheiro recomenda ou o recurso mais baixo; Armazém antes de encher e "
        "Fazenda antes de a população travar. Não construa fora da sua área."
    )
    tools = ("get_village_state", "upgrade_building", "unlock_scavenge")
    buildings = ("main", "wood", "stone", "iron", "farm", "storage", "hide", "market")

    def needs_llm(self, ctx: VillageContext, config: AgentSettings) -> bool:
        return False

    async def rules(self, box: "Toolbox") -> str:
        ctx = box.ctx
        notes = []

        planned = PlanTracker.next_builds(ctx.plan)
        built = await self.build_first_affordable(box, planned, limit=self.free_slots(box), reason="passo do plano")
        if built:
            notes.append(f"plano: {', '.join(built)}")

        for option_id in PlanTracker.next_unlocks(ctx.plan):
            if not box.guard.check_unlock_scavenge(ctx, option_id):
                outcome = await box.invoke("unlock_scavenge", {"option_id": option_id, "reason": "passo do plano"})
                notes.append(outcome.text)
                break

        if self.free_slots(box) and self.near_full(ctx):
            extra = [r.building for r in ctx.village.recommendations] + list(self.buildings)
            spent = await self.build_first_affordable(box, extra, limit=1, reason="armazém quase cheio: usar recursos")
            if spent:
                notes.append(f"excedente: {', '.join(spent)}")

        if self.free_slots(box):
            idle = ["main", *sorted(("wood", "stone", "iron"), key=lambda b: ctx.levels.get(b, 0)), "storage", "farm"]
            spent = await self.build_first_affordable(box, idle, limit=1, reason="fila livre: não deixar a construção parada")
            if spent:
                notes.append(f"fila livre: {', '.join(spent)}")

        if not notes:
            return "nada a construir agora (fila cheia, sem recursos ou plano em espera)"

        return "; ".join(notes)
