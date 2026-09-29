"""Quests: collect rewards and hand in finished missions."""

import re
from typing import TYPE_CHECKING

from tribal_assistant.core.agents.knobs import knob
from tribal_assistant.core.agents.quests import QuestRules
from tribal_assistant.core.agents.roles.base import VillageAgent

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox


class QuartermasterAgent(VillageAgent):
    key = "quartermaster"
    title = "Intendente de Missões"
    mission = (
        "Manter as missões em dia para liberar recursos grátis antes dos outros agentes gastarem: "
        "1) concluir com complete_quest cada missão marcada [pronta]; 2) coletar as recompensas prontas "
        "com claim_quest_rewards; 3) abrir os baús do bônus diário com open_daily_bonus (grátis, no máximo "
        "a cada 4 horas). Nunca gaste pontos premium. Nunca ative a milícia nem conclua missão de milícia: ela para a "
        "produção das minas."
    )
    tools = ("get_quests", "claim_quest_rewards", "complete_quest", "open_daily_bonus")

    def needs_llm(self, ctx, config) -> bool:
        return False

    async def rules(self, box: "Toolbox") -> str:
        done = []

        for quest in box.ctx.quests:
            if quest["can_complete"] and not QuestRules.forbidden(quest):
                outcome = await box.invoke("complete_quest", {"quest_id": quest["id"], "reason": "metas atingidas"})
                if outcome.ok:
                    done.append(f"missão {quest['id']}")

        overflow = await self.overflow(box) if box.ctx.rewards_pending else []
        if overflow:
            done.append(f"recompensas guardadas: {', '.join(overflow)} estouraria o armazém")
        elif box.ctx.rewards_pending:
            outcome = await box.invoke("claim_quest_rewards", {"reason": "recompensas prontas"})
            if outcome.ok:
                done.append(outcome.text)

        from tribal_assistant.core.agents.tools.act import OpenDailyBonus

        hours = knob(box.ctx, "cooldown.daily_bonus")
        if OpenDailyBonus.due(hours) and await box.lessons.due(f"daily_bonus:{box.ctx.game_id}", hours):
            await box.lessons.mark(f"daily_bonus:{box.ctx.game_id}")
            outcome = await box.invoke("open_daily_bonus", {"reason": "baús diários grátis"})
            if outcome.ok:
                done.append(outcome.text)

        return "; ".join(done) or "nada a coletar"

    @staticmethod
    def reward_resources(label: str) -> tuple[int, int, int]:
        """Resources in a reward label like 'Poço de argila 5 150 150 100 Tudo' (the last three numbers)."""
        numbers = [int(n.replace(".", "")) for n in re.findall(r"\d[\d.]*", label)]
        if len(numbers) < 3:
            return 0, 0, 0

        wood, clay, iron = numbers[-3:]
        return wood, clay, iron

    async def overflow(self, box: "Toolbox") -> list[str]:
        """Resources that would pass storage if every pending reward were claimed now."""
        from tribal_assistant.core.repositories.agents import AgentRepository

        total = [0, 0, 0]
        for reward in await AgentRepository(box.session).pending_rewards():
            for i, amount in enumerate(self.reward_resources(reward.label)):
                total[i] += amount

        storage = box.ctx.village.storage or 0
        stock = [box.ctx.stock.get(r, 0) for r in ("wood", "clay", "iron")]
        names = ("madeira", "argila", "ferro")
        return [names[i] for i in range(3) if storage and stock[i] + total[i] > storage]
