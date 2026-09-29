"""Guided workflows exposed as MCP prompts."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

VillageArg = Annotated[str, Field(description="Own village id from get_overview; empty means ask, or use the only village.")]

CONFIRM = (
    "Every game action runs first with dry_run=true. Show the user the list of dry-run results in one "
    "short table, wait for an explicit yes in a later message, then repeat only the approved calls with "
    "dry_run=false. A RECUSADO answer is final for this turn: report the reason, do not retry with other "
    "arguments to get around it. Never spend premium points and never touch player villages."
)


class Prompts:
    @staticmethod
    def village(village_id: str) -> str:
        return village_id or "not given: take it from get_overview (ask the user when there is more than one village)"

    def register(self, mcp: MCPServer) -> None:
        @mcp.prompt(
            title="Grow a village",
            description="Read one village, propose the next builds, recruits and scavenging, and act on approval.",
        )
        def grow_village(village_id: VillageArg = "") -> str:
            return (
                "Goal: grow one Tribal Wars village this turn without wasting resources.\n\n"
                f"Village: {self.village(village_id)}.\n\n"
                "1. Call sync_account once, then get_village_state for the village and get_quests.\n"
                "2. Stop and warn the user if the state shows ATAQUES CHEGANDO; suggest defence instead of spending.\n"
                "3. Pick at most two builds and one recruit batch, in this priority:\n"
                "   a. quest goals that are close (they pay resources);\n"
                "   b. Armazém when any resource is above 85% of storage;\n"
                "   c. Fazenda when free population is below 10%;\n"
                "   d. the lowest of Bosque, Poço de argila and Mina de ferro;\n"
                "   e. the current plan's next pending step (get_plans).\n"
                "   Use lookup_knowledge only when a requirement is unclear; skip anything the state marks as blocked.\n"
                "4. If a scavenging tier is locked and the previous one is open, include unlock_scavenge.\n"
                "5. Call upgrade_building / recruit_units / unlock_scavenge with dry_run=true, each with a short reason.\n"
                f"6. {CONFIRM}\n"
                "7. Finish with set_village_goal only if the priorities changed, and a two-line summary: what was queued, what comes next."
            )

        @mcp.prompt(
            title="Farm round",
            description="Loot nearby barbarian villages with the troops at home, then send idle troops scavenging.",
        )
        def farm_round(village_id: VillageArg = "") -> str:
            return (
                "Goal: one safe looting round on barbarian villages.\n\n"
                f"Village: {self.village(village_id)}.\n\n"
                "1. Call get_village_state. If it shows ATAQUES CHEGANDO, stop: troops stay home.\n"
                "2. Call get_world_status; if fetched_at is empty or older than a day, call sync_world.\n"
                "3. Call list_barbarians for the village. Drop targets with recently_attacked=true.\n"
                "4. Plan up to 3 attacks on the closest low-point targets. Squad per target: 5 light "
                "(best, carries 80 each), else 10 spear, else 10 axe. Only use troops at home and keep "
                "some spearmen home for defence.\n"
                "5. Call send_farm_attack with dry_run=true for each target and a reason.\n"
                "6. With the troops left idle, propose send_scavenge on the highest free tier (dry_run=true).\n"
                f"7. {CONFIRM}\n"
                "8. Report targets hit, arrival times and troops left home in three lines."
            )

        @mcp.prompt(
            title="Path to the first nobleman",
            description="Plan the builds for the Academy and the first nobleman and save them as the village plan.",
        )
        def first_noble_plan(village_id: VillageArg = "") -> str:
            return (
                "Goal: an ordered, realistic plan to the first nobleman, saved so the agents follow it.\n\n"
                f"Village: {self.village(village_id)}.\n\n"
                "1. Call lookup_knowledge kind=building id=snob and kind=unit id=snob (Academy needs "
                "Edifício principal 20, Ferreiro 20, Mercado 10; a nobleman costs 40000/50000/50000 and 100 population).\n"
                "2. Call get_village_state and get_plans; list the gap for each requirement.\n"
                "3. Keep the economy able to pay: interleave Armazém (a nobleman needs 50000 storage), "
                "Fazenda and the resource pits with the requirement builds.\n"
                "4. Build at most 12 steps, most urgent first. Build steps name the level to reach; "
                "recruit steps the total troops to own (escort troops: the nobleman dies if sent alone).\n"
                "5. Show the plan as a numbered list with a rough resource total, and ask for a yes.\n"
                "6. On yes, save it with set_village_plan (summary + steps) and set_village_goal in one sentence.\n"
                "Remind the user: conquering takes several noble attacks in a row (loyalty drops 20-35 per hit)."
            )

        @mcp.prompt(
            title="Agent round",
            description="Show the agent configuration, simulate a full agent round, then run it live on approval.",
        )
        def agent_round() -> str:
            return (
                "Goal: one supervised round of the village agents.\n\n"
                "1. Call get_agents_config and tell the user in two lines: brain (LLM model or rules), "
                "schedule, global dry-run and the main guardrails.\n"
                "2. Call sync_account if the last sync may be stale.\n"
                "3. Call run_agents with dry_run=true. Summarise per village and per agent in one line each; "
                "flag RECUSADO answers and errors.\n"
                "4. Ask for a yes. Only in a later message, call run_agents with dry_run=false.\n"
                "5. Call get_agent_decisions (limit 30) and report what the game answered: done, refused, failed.\n"
                "Do not change settings with update_agent_settings unless the user asks."
            )

        @mcp.prompt(
            title="Daily routine",
            description="Free resources first: quests, rewards, the daily bonus and scavenging on every village.",
        )
        def daily_routine() -> str:
            return (
                "Goal: collect everything free on the account, then report what needs attention.\n\n"
                "1. Call sync_account, then get_overview once for the village list and incoming attacks.\n"
                "2. Call get_quests. For each quest with can_complete=true, plan complete_quest; then "
                "claim_quest_rewards on the village with the most free storage.\n"
                "3. If the player's daily_bonus is waiting, plan open_daily_bonus on any village.\n"
                "4. For each village without incoming attacks, call get_village_state and plan send_scavenge "
                "with idle troops on the highest free tier.\n"
                "5. Run all of the above with dry_run=true.\n"
                f"6. {CONFIRM}\n"
                "7. End with a short list: collected, queued, and warnings (storage above 85%, attacks, full population)."
            )
