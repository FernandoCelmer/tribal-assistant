"""MCP server: account state, world data, farm list and guarded game actions."""

import argparse
from collections.abc import Sequence

from mcp.server.mcpserver import MCPServer

from tribal_assistant.core.config import settings
from tribal_assistant.core.logging import configure_logging
from tribal_assistant.mcp.prompts import Prompts
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.mcp.tools.farm import FarmTools
from tribal_assistant.mcp.tools.game import GameActionTools
from tribal_assistant.mcp.tools.state import StateTools
from tribal_assistant.mcp.tools.world import WorldTools
from tribal_assistant.version import __version__

INSTRUCTIONS = """\
Tribal Assistant: read and play a Tribal Wars account through a real browser session.

Start with get_overview (call sync_account first when data may be stale) and get_quests.
Village ids in every tool come from get_overview. lookup_knowledge answers building
requirements and unit stats from the game's help pages. list_nearby and
list_farm_targets find barbarian villages; get_agent_decisions shows what the
village agents did and why.

Game actions (upgrade_building, recruit_units, send_farm_attack, claim_quest_rewards,
complete_quest, run_agents) default to dry_run=true: show the user what would happen,
then call again with dry_run=false only after an explicit yes.
"""

RULES = """
Rules, whatever the client:
- Every game action passes the guardrails: resource reserve, recruit budget, build
  queue slots, attack radius, hourly attack limit, and barbarian-only targets. When a
  tool answers RECUSADO, report the reason and stop; do not look for another way.
- Never attack player villages, never sell or send resources, never run actions in a
  loop without the user watching.
- Automating the game breaks Tribal Wars rules and can get the account banned; the
  user accepted that risk for this account. Keep actions human-paced and few.
"""


class TribalMcpServer:
    GROUPS: tuple[type[ToolGroup], ...] = (StateTools, WorldTools, FarmTools, GameActionTools)

    def build(self) -> MCPServer:
        mcp = MCPServer("tribal-assistant", instructions=INSTRUCTIONS + RULES, version=__version__)

        for group in self.GROUPS:
            group().register(mcp)

        Prompts().register(mcp)
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
