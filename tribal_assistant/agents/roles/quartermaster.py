"""Quests: collect rewards and hand in finished missions."""

from typing import TYPE_CHECKING

from tribal_assistant.agents.roles.base import VillageAgent

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox


class QuartermasterAgent(VillageAgent):
    key = "quartermaster"
    title = "Intendente de Missões"
    mission = (
        "Manter as missões em dia para liberar recursos grátis antes dos outros agentes gastarem: "
        "1) concluir com complete_quest cada missão marcada [pronta]; 2) coletar as recompensas prontas "
        "com claim_quest_rewards; 3) abrir os baús do bônus diário com open_daily_bonus (grátis, no máximo "
        "a cada 4 horas). Nunca gaste pontos premium."
    )
    tools = ("get_quests", "claim_quest_rewards", "complete_quest", "open_daily_bonus")

    def needs_llm(self, ctx, config) -> bool:
        return False

    async def rules(self, box: "Toolbox") -> str:
        done = []

        for quest in box.ctx.quests:
            if quest["can_complete"]:
                outcome = await box.invoke("complete_quest", {"quest_id": quest["id"], "reason": "metas atingidas"})
                if outcome.ok:
                    done.append(f"missão {quest['id']}")

        storage = box.ctx.village.storage or 0
        fullest = max(box.ctx.stock.get(r, 0) for r in ("wood", "clay", "iron"))
        if box.ctx.rewards_pending and storage and fullest >= storage * 0.9:
            done.append("armazém quase cheio: recompensas guardadas para não desperdiçar")
        elif box.ctx.rewards_pending:
            outcome = await box.invoke("claim_quest_rewards", {"reason": "recompensas prontas"})
            if outcome.ok:
                done.append(outcome.text)

        from tribal_assistant.agents.tools.act import OpenDailyBonus

        if OpenDailyBonus.due():
            outcome = await box.invoke("open_daily_bonus", {"reason": "baús diários grátis"})
            if outcome.ok:
                done.append(outcome.text)

        return "; ".join(done) or "nada a coletar"
