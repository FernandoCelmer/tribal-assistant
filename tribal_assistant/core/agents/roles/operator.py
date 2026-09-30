"""The human (or an MCP client) acting directly, still through the guardrails and the decision log."""

from typing import TYPE_CHECKING

from tribal_assistant.core.agents.roles.base import VillageAgent

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox


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
        "search_docs",
        "read_doc",
        "list_barbarians",
        "get_target_intel",
        "read_farm_assistant",
        "get_incoming",
        "simulate_battle",
        "get_forecast",
        "plan_scavenge",
        "get_own_offers",
        "send_spy",
        "park_market_offer",
        "cancel_market_offer",
        "send_resources",
        "send_noble",
        "upgrade_building",
        "recruit_units",
        "send_farm_attack",
        "send_farm_template",
        "set_farm_templates",
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
        "set_profile_text",
        "assign_flag",
        "learn_knight_skill",
        "train_knight",
        "accept_market_offer",
        "create_market_offer",
        "research_unit",
        "apply_to_tribe",
        "accept_tribe_invite",
        "accept_mentor",
        "read_inbox",
        "read_thread",
        "read_tribe",
        "reply_mail",
        "send_mail",
        "accept_friend",
        "add_friend",
        "reply_forum",
    )

    async def rules(self, box: "Toolbox") -> str:
        return "operador não tem política automática"
