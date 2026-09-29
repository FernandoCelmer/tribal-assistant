"""Public world data around your villages."""

import json
from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from tribal_assistant.mcp.annotations import READ_ONLY, READS_GAME, GuardedTool
from tribal_assistant.mcp.schemas import BarbarianTarget, BarbarianTargets, Nearby, SyncOutcome
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.mcp.tools.bridge import ToolboxBridge
from tribal_assistant.schemas.world import WorldStatus
from tribal_assistant.services.world import WorldService


class WorldTools(ToolGroup):
    def __init__(self) -> None:
        self.bridge = ToolboxBridge()

    def register(self, mcp: MCPServer) -> None:
        @GuardedTool(mcp, title="World data status", annotations=READ_ONLY)
        async def get_world_status() -> WorldStatus:
            """How much public world data is stored locally (villages, players, tribes), the world and
            unit speed, and when it was downloaded. When fetched_at is empty or older than a day,
            call sync_world before list_nearby or list_barbarians.
            """
            return await self.with_session(lambda s: WorldService(s).status())

        @GuardedTool(mcp, title="Nearby villages", annotations=READ_ONLY)
        async def list_nearby(
            kind: Annotated[Literal["barbarian", "player", "all"], Field(description="barbarian (no owner), player, or all.")] = "barbarian",
            radius: Annotated[int, Field(ge=1, le=100, description="Search radius in fields.")] = 15,
            limit: Annotated[int, Field(ge=1, le=200, description="Maximum rows, closest first.")] = 30,
            village_id: Annotated[int | None, Field(description="Origin own village id from get_overview; default is the first own village.")] = None,
        ) -> Nearby:
            """Villages around one of yours from the public world data: coords, points, distance,
            owner and tribe, whether it is barbarian or already a farm target, and travel minutes
            per unit. For scouting neighbours and threats; for picking loot targets prefer
            list_barbarians, which also flags targets hit recently and respects the role's attack radius.
            """
            rows = await self.with_session(lambda s: WorldService(s).nearby(village_id, kind, radius, limit))
            return Nearby(villages=rows)

        @GuardedTool(mcp, title="Barbarian loot targets", annotations=READ_ONLY)
        async def list_barbarians(
            village_id: Annotated[int, Field(description="Origin own village id from get_overview.")],
            radius: Annotated[int | None, Field(ge=1, le=50, description="Search radius; capped at the role's attack radius guardrail.")] = None,
            limit: Annotated[int, Field(ge=1, le=30, description="Maximum targets, closest first.")] = 10,
        ) -> BarbarianTargets:
            """Barbarian villages send_farm_attack would accept from this village: inside the role's attack radius,
            closest first, with points, distance, travel minutes per unit and recently_attacked
            (skip those; they are refused until the role's retarget time passes). Falls back to the local farm
            list when world data is missing; an empty list comes with a note on what to do.
            """
            args = {"limit": limit} | ({"radius": radius} if radius else {})
            outcome = await self.bridge.invoke(village_id, "list_barbarians", args, dry_run=True)

            if not outcome.text.startswith("["):
                return BarbarianTargets(targets=[], note=outcome.text)

            return BarbarianTargets(targets=[BarbarianTarget(**row) for row in json.loads(outcome.text)])

        @GuardedTool(mcp, title="Download world data", annotations=READS_GAME)
        async def sync_world() -> SyncOutcome:
            """Download the public world files (villages, players, tribes, world speeds) into the local
            database. Read-only on the game side and account-independent; the files change about
            once an hour, so once a day is enough for looting.
            """
            from tribal_assistant.client.modules.world_sync import sync_world as download
            from tribal_assistant.db.session import init_db

            await init_db()
            await download()
            return SyncOutcome(ok=True, message="dados do mundo atualizados")
