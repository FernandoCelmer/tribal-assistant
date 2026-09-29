"""MCP server: account state, world data, farm list, guarded game actions, knowledge resources and workflow prompts."""

import argparse
from collections.abc import Sequence

from mcp.server.mcpserver import MCPServer

from tribal_assistant.core.config import settings
from tribal_assistant.core.logging import configure_logging
from tribal_assistant.mcp.prompts import Prompts
from tribal_assistant.mcp.resources import Resources
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.mcp.tools.farm import FarmTools
from tribal_assistant.mcp.tools.game import GameActionTools
from tribal_assistant.mcp.tools.state import StateTools
from tribal_assistant.mcp.tools.world import WorldTools
from tribal_assistant.version import __version__

INSTRUCTIONS = """\
Tribal Assistant: read and play one Tribal Wars (pt-BR) account through a real browser session.
Game-facing text (village state, refusals, quest titles) is Portuguese; answer the user in their language.

Reading, cheapest first:
- get_overview lists every own village with its id; every other tool takes that id, never coords.
- get_village_state gives one village in a few hundred tokens; prefer it over get_overview.
- get_quests, get_plans, get_agent_decisions and get_agents_config explain progress and past actions.
- lookup_knowledge answers building requirements and unit stats from the official help pages.
- list_barbarians gives loot targets that the guardrails accept; list_nearby scouts the map.
- Data is as fresh as the last sync_account (game) and sync_world (public map); sync once per
  session or after acting, not before every read.
Resources mirror the static parts: tribal://knowledge/strategy, tribal://knowledge/buildings,
tribal://knowledge/units, tribal://plans and tribal://village/{village_id}/state.

Acting:
- Game actions (upgrade_building, recruit_units, send_farm_attack, send_scavenge,
  unlock_scavenge, claim_quest_rewards, complete_quest, open_daily_bonus, run_agents) default
  to dry_run=true. Show the user what would happen, then call again with dry_run=false only
  after an explicit yes in a later message.
- set_village_plan and set_village_goal only change what the agents do next; they replace the
  current plan or goal, so read get_plans first.
- Every action needs a short reason; it is stored in the decision log.
- Prompts grow_village, farm_round, first_noble_plan, agent_round and daily_routine walk
  through the common workflows.
"""

RULES = """
Rules, whatever the client:
- Every game action passes the guardrails: resource reserve, recruit budget, build queue
  slots, attack radius, hourly attack limit, retarget delay and barbarian-only targets. When a
  tool answers RECUSADO, report the reason and stop; do not look for another way around it.
- Never attack player villages, never sell, trade or send resources, never spend premium
  points, and never run actions in a loop without the user watching.
- Keep troops home when an attack is incoming (ATAQUES CHEGANDO in the village state).
- Automating the game breaks Tribal Wars rules and can get the account banned; the user
  accepted that risk for this account. Keep actions human-paced and few.
"""


class TribalMcpServer:
    GROUPS: tuple[type[ToolGroup], ...] = (StateTools, WorldTools, FarmTools, GameActionTools)

    def build(self) -> MCPServer:
        mcp = MCPServer(
            "tribal-assistant",
            title="Tribal Assistant",
            description="Play a Tribal Wars account through guarded, logged actions.",
            instructions=INSTRUCTIONS + RULES,
            version=__version__,
        )

        for group in self.GROUPS:
            group().register(mcp)

        Prompts().register(mcp)
        Resources().register(mcp)
        return mcp

    @staticmethod
    def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
        parser = argparse.ArgumentParser(prog="tribal-assistant-mcp", description=__doc__)
        parser.add_argument("--http", action="store_true", help="Serve streamable HTTP instead of stdio.")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8765)
        return parser.parse_args(argv)

    def main(self, argv: Sequence[str] | None = None) -> None:
        configure_logging(settings.log_level)
        args = self.parse_args(argv)
        mcp = self.build()

        if args.http:
            mcp.run(transport="streamable-http", host=args.host, port=args.port)
            return

        mcp.run()


def main(argv: Sequence[str] | None = None) -> None:
    TribalMcpServer().main(argv)
