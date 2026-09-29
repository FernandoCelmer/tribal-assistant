"""Public world data around your villages."""

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from tribal_assistant.mcp.annotations import REACHES_OUT, READ_ONLY, GuardedTool
from tribal_assistant.mcp.schemas import Nearby, SyncOutcome
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.schemas.world import WorldStatus
from tribal_assistant.services.world import WorldService


class WorldTools(ToolGroup):
    def register(self, mcp: MCPServer) -> None:
        @GuardedTool(mcp, annotations=READ_ONLY)
        async def get_world_status() -> WorldStatus:
            """How much public world data is stored locally and when it was downloaded."""
            return await self.with_session(lambda s: WorldService(s).status())

        @GuardedTool(mcp, annotations=READ_ONLY)
        async def list_nearby(
            kind: Annotated[Literal["barbarian", "player", "all"], Field(description="Which villages.")] = "barbarian",
            radius: Annotated[int, Field(ge=1, le=100, description="Search radius in fields.")] = 15,
            limit: Annotated[int, Field(ge=1, le=200, description="Maximum rows, closest first.")] = 30,
            village_id: Annotated[int | None, Field(description="Origin village id; default is the first own village.")] = None,
        ) -> Nearby:
            """Villages around one of yours with distance, owner, tribe and travel minutes per unit."""
            rows = await self.with_session(lambda s: WorldService(s).nearby(village_id, kind, radius, limit))
            return Nearby(villages=rows)

        @GuardedTool(mcp, annotations=REACHES_OUT)
        async def sync_world() -> SyncOutcome:
            """Download the public world files (villages, players, tribes, speeds). Read-only on the game side."""
            from tribal_assistant.client.modules.world_sync import sync_world as download
            from tribal_assistant.db.session import init_db

            await init_db()
            await download()
            return SyncOutcome(ok=True, message="dados do mundo atualizados")
