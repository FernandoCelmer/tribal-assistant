"""Read-only context exposed as MCP resources: game knowledge, plans and one village's state."""

from mcp.server.mcpserver import MCPServer

from tribal_assistant.mcp.client import ApiClient


class Resources:
    def __init__(self, api: ApiClient | None = None) -> None:
        self.api = api or ApiClient()

    def register(self, mcp: MCPServer) -> None:
        @mcp.resource(
            "tribal://knowledge/strategy",
            title="Base strategy",
            description="The playbook every agent follows, from the pt-BR help pages.",
            mime_type="text/markdown",
        )
        async def strategy() -> str:
            return await self.api.get("/knowledge/strategy")

        @mcp.resource(
            "tribal://knowledge/guide/{name}",
            title="Game guide",
            description="Full pt-BR guide: inicio (first days), avancado (many villages, tribe) or nobre (conquest).",
            mime_type="text/markdown",
        )
        async def guide(name: str) -> str:
            return await self.api.get(f"/knowledge/guides/{name}")

        @mcp.resource(
            "tribal://lessons",
            title="Lessons learned",
            description="What the assistant learned while playing: failed actions and why, game notices, quests seen and finished.",
            mime_type="application/json",
        )
        async def lessons() -> list[dict]:
            return await self.api.get("/agents/lessons", limit=200)

        @mcp.resource(
            "tribal://knowledge/buildings",
            title="Buildings",
            description="Every documented building: label, max level, requirements and role.",
            mime_type="application/json",
        )
        async def buildings() -> dict:
            return await self.api.get("/knowledge/buildings")

        @mcp.resource(
            "tribal://knowledge/units",
            title="Units",
            description="Every documented unit: cost, population, attack, defense, speed, carry and requirement.",
            mime_type="application/json",
        )
        async def units() -> dict:
            return await self.api.get("/knowledge/units")

        @mcp.resource(
            "tribal://plans",
            title="Village plans",
            description="Each village's plan with live step status, as get_plans returns it.",
            mime_type="application/json",
        )
        async def plans() -> list:
            return await self.api.get("/agents/plans")

        @mcp.resource(
            "tribal://village/{village_id}/state",
            title="Village state",
            description="Compact pt-BR summary of one own village (id from get_overview), as the agents see it.",
            mime_type="text/plain",
        )
        async def village_state(village_id: str) -> str:
            outcome = await self.api.post(
                "/agents/act",
                {"village_id": int(village_id), "tool": "get_village_state", "arguments": {}, "dry_run": True, "source": "mcp"},
            )
            return outcome["detail"]
