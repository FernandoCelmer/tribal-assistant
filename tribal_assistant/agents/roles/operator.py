"""The human (or an MCP client) acting directly, still through the guardrails and the decision log."""

from typing import TYPE_CHECKING

from tribal_assistant.agents.roles.base import VillageAgent

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox


class OperatorAgent(VillageAgent):
    key = "operator"
    title = "Operador"
    mission = (
        "Executar ordens diretas do jogador, uma de cada vez, sempre dentro das travas de segurança. "
        "Não tome iniciativa além do pedido, não contorne um RECUSADO e responda com o resultado do jogo."
    )
    tools = (
        "get_village_state",
        "get_quests",
        "lookup_knowledge",
        "list_barbarians",
        "upgrade_building",
        "recruit_units",
        "send_farm_attack",
        "claim_quest_rewards",
        "complete_quest",
        "set_village_goal",
        "unlock_scavenge",
        "send_scavenge",
        "set_village_plan",
        "open_daily_bonus",
        "recruit_knight",
        "use_item",
        "choose_relic",
        "equip_relic",
        "rename_village",
        "assign_flag",
        "learn_knight_skill",
    )

    async def rules(self, box: "Toolbox") -> str:
        return "operador não tem política automática"
