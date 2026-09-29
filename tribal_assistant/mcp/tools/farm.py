"""Local list of barbarian farm targets."""

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from tribal_assistant.mcp.annotations import READ_ONLY, WRITES_LOCAL, GuardedTool
from tribal_assistant.mcp.schemas import FarmTargets
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.repositories.farm import FarmTargetRepository
from tribal_assistant.schemas.farm import FarmTarget, FarmTargetCreate
from tribal_assistant.services.farm import FarmService


class FarmTools(ToolGroup):
    def register(self, mcp: MCPServer) -> None:
        @GuardedTool(mcp, annotations=READ_ONLY)
        async def list_farm_targets(
            include_disabled: Annotated[bool, Field(description="Also list disabled targets.")] = False,
        ) -> FarmTargets:
            """Farm targets the raider agent may use when world data is missing."""
            rows = await self.with_session(
                lambda s: FarmTargetRepository(s).list(enabled_only=not include_disabled)
            )
            return FarmTargets(targets=[FarmTarget.model_validate(r) for r in rows])

        @GuardedTool(mcp, annotations=WRITES_LOCAL)
        async def add_farm_target(
            coords: Annotated[str, Field(description="Barbarian village coordinates x|y.")],
            template: Annotated[Literal["A", "B", "C"], Field(description="Loot assistant template.")] = "A",
            wall_level: Annotated[int, Field(ge=0, le=20, description="Known wall level.")] = 0,
        ) -> FarmTarget:
            """Add a farm target to the local list. Nothing is sent to the game."""
            payload = FarmTargetCreate(coords=coords, template=template, wall_level=wall_level)
            row = await self.with_session(lambda s: FarmService(s).add(payload))
            return FarmTarget.model_validate(row)

        @GuardedTool(mcp, annotations=WRITES_LOCAL)
        async def remove_farm_target(
            target_id: Annotated[int, Field(description="Target id from list_farm_targets.")],
        ) -> FarmTargets:
            """Remove a farm target from the local list and return what remains."""
            await self.with_session(lambda s: FarmService(s).remove(target_id))
            rows = await self.with_session(lambda s: FarmTargetRepository(s).list(enabled_only=False))
            return FarmTargets(targets=[FarmTarget.model_validate(r) for r in rows])
