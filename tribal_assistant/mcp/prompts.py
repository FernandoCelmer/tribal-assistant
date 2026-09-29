"""Guided workflows exposed as MCP prompts."""

from mcp.server.mcpserver import MCPServer


class Prompts:
    def register(self, mcp: MCPServer) -> None:
        @mcp.prompt(title="Grow a village", description="Read the village, plan the next builds and recruits, act on approval.")
        def grow_village(village_id: str = "") -> str:
            return (
                "Grow one Tribal Wars village.\n\n"
                f"Village: {village_id or 'ask the user, or use the first village from get_overview'}.\n"
                "1. Call sync_account, then get_overview and get_quests.\n"
                "2. Call lookup_knowledge for anything whose requirements are unclear.\n"
                "3. Propose up to two builds and one recruit batch, prioritising quest goals, storage before it fills and farm before population locks.\n"
                "4. Call upgrade_building / recruit_units with dry_run=true and show the results.\n"
                "5. Wait for a yes, then repeat with dry_run=false. Never call with dry_run=false in the same turn as the proposal.\n"
                "6. Finish with set_village_goal summarising the plan."
            )

        @mcp.prompt(title="Farm round", description="Loot nearby barbarian villages with the troops at home.")
        def farm_round(village_id: str = "") -> str:
            return (
                "Run one looting round on barbarian villages.\n\n"
                f"Village: {village_id or 'first village from get_overview'}.\n"
                "1. Call get_overview and check troops at home and incoming attacks; if an attack is incoming, stop.\n"
                "2. Call list_nearby with kind=barbarian.\n"
                "3. Plan small squads (5 light cavalry or 10 spearmen) for the closest targets.\n"
                "4. Call send_farm_attack with dry_run=true for each, show the plan, wait for a yes.\n"
                "5. Then send with dry_run=false. Never target player villages."
            )

        @mcp.prompt(title="Path to the first nobleman", description="Plan the builds needed for the Academy and the first nobleman.")
        def first_noble_plan(village_id: str = "") -> str:
            return (
                "Plan the path to the first nobleman.\n\n"
                f"Village: {village_id or 'first village from get_overview'}.\n"
                "1. Call lookup_knowledge kind=building id=snob and kind=unit id=snob.\n"
                "2. Call get_overview and compare current levels with Headquarters 20, Smithy 20, Market 10.\n"
                "3. Write an ordered build plan with rough resource totals.\n"
                "4. Save it with set_village_goal so the agents follow it."
            )

        @mcp.prompt(title="Agent round", description="Simulate a full agent round, review, then run it live on approval.")
        def agent_round() -> str:
            return (
                "Run the village agents.\n\n"
                "1. Call get_agents_config and tell the user the brain, schedule and limits.\n"
                "2. Call run_agents with dry_run=true and summarise each agent's plan per village.\n"
                "3. Wait for a yes, then call run_agents with dry_run=false.\n"
                "4. Call get_agent_decisions to report what the game answered."
            )
