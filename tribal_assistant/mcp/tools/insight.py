"""Read-only views for planning: reports, forecasts, scavenging split, and live market, paladin and inventory."""

from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from tribal_assistant.mcp.annotations import READ_ONLY, READS_GAME, GuardedTool
from tribal_assistant.mcp.tools.base import ToolGroup

VILLAGE = Field(description="Own village id from get_overview; omit for the first own village.")


class InsightTools(ToolGroup):
    def register(self, mcp: MCPServer) -> None:
        @GuardedTool(mcp, title="Battle reports", annotations=READ_ONLY)
        async def get_reports(
            offset: Annotated[int, Field(ge=0, description="Rows to skip, for the next page.")] = 0,
            limit: Annotated[int, Field(ge=1, le=200, description="Rows per page, newest first.")] = 30,
            category: Annotated[str | None, Field(description="Only this category (attack, defense, trade, support, other...).")] = None,
            result: Annotated[str | None, Field(description="Only this dot colour: green, yellow, red, blue.")] = None,
            coords: Annotated[str | None, Field(description="Only reports where x|y is the origin or the target.")] = None,
        ) -> dict[str, Any]:
            """Synced report inbox, newest first and paged: title, category, result colour, origin and
            target coords, loot per resource and haul. total says how many match, for paging. Use it to
            judge a barbarian target (green hauls vs yellow losses) or to explain what happened while
            away. As fresh as the last sync_account.
            """
            return await self.api.get("/game/reports", offset=offset, limit=limit, category=category, result=result, coords=coords)

        @GuardedTool(mcp, title="Village forecast", annotations=READ_ONLY)
        async def get_forecast(
            village_id: Annotated[int | None, VILLAGE] = None,
            wood: Annotated[int, Field(ge=0, description="Optional cost to check: wood.")] = 0,
            clay: Annotated[int, Field(ge=0, description="Optional cost to check: clay.")] = 0,
            iron: Annotated[int, Field(ge=0, description="Optional cost to check: iron.")] = 0,
        ) -> dict[str, Any]:
            """Per-village forecast at the current production: hours (and time) until each resource fills
            the storage, until the farm locks population, until the build queue ends and until the next
            incoming attack lands; when the next plan build becomes affordable and, when a cost is given,
            when that cost is. A null hour means never at this pace. Reads the local database only.
            """
            return {"villages": await self.api.get("/game/forecast", village_id=village_id, wood=wood, clay=clay, iron=iron)}

        @GuardedTool(mcp, title="Scavenging split", annotations=READ_ONLY)
        async def plan_scavenge(village_id: Annotated[int | None, VILLAGE] = None) -> dict[str, Any]:
            """How the troops at home would be shared over the free scavenging tiers so all runs end
            together and yield the most per minute (each part above the minimum population): units,
            carry, expected haul and base minutes per tier, ready for send_scavenge. Nothing is sent.
            """
            return {"villages": await self.api.get("/game/scavenge-plan", village_id=village_id)}

        @GuardedTool(mcp, title="Market", annotations=READS_GAME)
        async def get_market(village_id: Annotated[int | None, VILLAGE] = None) -> dict[str, Any]:
            """Live market of one village, read in the game: free merchants and carry, other players'
            offers (what you would receive and pay, travel minutes, whether you can accept) and your own
            open offers (parked=true is surplus kept in the merchants on purpose). Opens the game browser,
            so it only works on the server that plays; it never touches the premium exchange.
            """
            return await self.api.get("/game/market", village_id=village_id)

        @GuardedTool(mcp, title="Paladin", annotations=READS_GAME)
        async def get_knight(village_id: Annotated[int | None, VILLAGE] = None) -> dict[str, Any]:
            """Live paladin state at the statue: learnable skill ids, whether a paladin can be recruited
            and whether training is available. Opens the game browser; only on the server that plays.
            """
            return await self.api.get("/game/knight", village_id=village_id)

        @GuardedTool(mcp, title="Inventory", annotations=READS_GAME)
        async def get_inventory(village_id: Annotated[int | None, VILLAGE] = None) -> dict[str, Any]:
            """Live inventory: each item with key, name, detail text and whether it can be used now
            (resource packs, construction bonus, relics...). Opens the game browser; only on the server
            that plays. Using items is left to the agents.
            """
            return await self.api.get("/game/inventory", village_id=village_id)
