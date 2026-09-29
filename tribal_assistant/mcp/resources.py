"""Read-only context exposed as MCP resources: game knowledge, plans and one village's state."""

from mcp.server.mcpserver import MCPServer

from tribal_assistant.agents.knowledge import GameKnowledge
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.mcp.tools.bridge import ToolboxBridge
from tribal_assistant.services.agents import AgentService


class Resources:
    def __init__(self) -> None:
        self.bridge = ToolboxBridge()

    def register(self, mcp: MCPServer) -> None:
        @mcp.resource(
            "tribal://knowledge/strategy",
            title="Base strategy",
            description="The playbook every agent follows, from the pt-BR help pages.",
            mime_type="text/markdown",
        )
        def strategy() -> str:
            return GameKnowledge.strategy

        @mcp.resource(
            "tribal://knowledge/guide/{name}",
            title="Game guide",
            description="Full pt-BR guide: inicio (first days), avancado (many villages, tribe) or nobre (conquest).",
            mime_type="text/markdown",
        )
        def guide(name: str) -> str:
            return GameKnowledge.guide(name) or f"guia desconhecido; use {', '.join(GameKnowledge.guides)}"

        @mcp.resource(
            "tribal://knowledge/buildings",
            title="Buildings",
            description="Every documented building: label, max level, requirements and role.",
            mime_type="application/json",
        )
        def buildings() -> dict:
            return {key: GameKnowledge.building(key) for key in GameKnowledge.buildings}

        @mcp.resource(
            "tribal://knowledge/units",
            title="Units",
            description="Every documented unit: cost, population, attack, defense, speed, carry and requirement.",
            mime_type="application/json",
        )
        def units() -> dict:
            return {key: GameKnowledge.unit(key) for key in GameKnowledge.units}

        @mcp.resource(
            "tribal://plans",
            title="Village plans",
            description="Each village's plan with live step status, as get_plans returns it.",
            mime_type="application/json",
        )
        async def plans() -> list:
            rows = await ToolGroup.with_session(lambda s: AgentService(s).plans())
            return [row.model_dump(mode="json") for row in rows]

        @mcp.resource(
            "tribal://village/{village_id}/state",
            title="Village state",
            description="Compact pt-BR summary of one own village (id from get_overview), as the agents see it.",
            mime_type="text/plain",
        )
        async def village_state(village_id: str) -> str:
            outcome = await self.bridge.invoke(int(village_id), "get_village_state", {}, dry_run=True)
            return outcome.text
