"""Quests: collect rewards and hand in finished missions."""

from typing import TYPE_CHECKING

from tribal_assistant.agents.roles.base import VillageAgent

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox


class QuartermasterAgent(VillageAgent):
    key = "quartermaster"
    title = "Intendente de Missões"
    mission = (
        "Manter as missões em dia: coletar recompensas prontas e concluir missões cujas metas foram "
        "atingidas, para liberar recursos grátis antes dos outros agentes gastarem."
    )
    tools = ("get_quests", "claim_quest_rewards", "complete_quest")

    def needs_llm(self, ctx, config) -> bool:
        return False

    async def rules(self, box: "Toolbox") -> str:
        done = []

        for quest in box.ctx.quests:
            if quest["can_complete"]:
                outcome = await box.invoke("complete_quest", {"quest_id": quest["id"], "reason": "metas atingidas"})
                if outcome.ok:
                    done.append(f"missão {quest['id']}")

        if box.ctx.rewards_pending:
            outcome = await box.invoke("claim_quest_rewards", {"reason": "recompensas prontas"})
            if outcome.ok:
                done.append(outcome.text)

        return "; ".join(done) or "nada a coletar"
