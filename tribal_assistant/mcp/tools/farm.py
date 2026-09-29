"""Local list of barbarian farm targets."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from tribal_assistant.mcp.annotations import READ_ONLY, REPLACES_LOCAL, WRITES_LOCAL, GuardedTool
from tribal_assistant.mcp.schemas import FarmTargets
from tribal_assistant.mcp.tools.base import ToolGroup


class FarmTools(ToolGroup):
    def register(self, mcp: MCPServer) -> None:
        @GuardedTool(mcp, title="Farm list", annotations=READ_ONLY)
        async def list_farm_targets(
            include_disabled: Annotated[bool, Field(description="Also list disabled targets.")] = False,
        ) -> FarmTargets:
            """Local list of barbarian farm targets with template, known wall level, last attack and
            last loot. The raider and list_barbarians fall back on it when world data is missing, and
            the guardrails accept its coords as barbarian. Not the game's loot assistant.
            """
            rows = await self.api.get("/farm/targets")
            return FarmTargets(targets=[r for r in rows if include_disabled or r.get("enabled", True)])

        @GuardedTool(mcp, title="Add farm target", annotations=WRITES_LOCAL)
        async def add_farm_target(
            coords: Annotated[str, Field(pattern=r"^\d{1,3}\|\d{1,3}$", description="Barbarian village coordinates x|y, e.g. 498|503.")],
            template: Annotated[Literal["A", "B", "C"], Field(description="Squad template label: A small, B larger, C sized from a spy report.")] = "A",
            wall_level: Annotated[int, Field(ge=0, le=20, description="Known wall level from a report; above 0 means the squad takes losses.")] = 0,
        ) -> dict[str, Any]:
            """Add a barbarian village to the local farm list. Nothing is sent to the game.

            Only add villages confirmed barbarian (list_nearby kind=barbarian): anything on this
            list passes the barbarian-only guardrail, so a player village here would be attacked.
            """
            return await self.api.post("/farm/targets", {"coords": coords, "template": template, "wall_level": wall_level})

        @GuardedTool(mcp, title="Remove farm target", annotations=REPLACES_LOCAL)
        async def remove_farm_target(
            target_id: Annotated[int, Field(ge=1, description="Target id from list_farm_targets.")],
        ) -> FarmTargets:
            """Delete a target from the local farm list (e.g. it became a player village or has a wall) and return what remains."""
            await self.api.delete(f"/farm/targets/{target_id}")
            return FarmTargets(targets=await self.api.get("/farm/targets"))
