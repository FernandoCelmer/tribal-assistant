"""Actions in the live game. All pass the agent guardrails and are logged; dry_run defaults to true."""

from typing import Annotated, Any
from uuid import uuid4

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from tribal_assistant.agents.context import ContextLoader
from tribal_assistant.agents.roles.operator import OperatorAgent
from tribal_assistant.agents.runner import AgentRunner
from tribal_assistant.agents.toolbox import Toolbox
from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.mcp.annotations import REACHES_OUT, WRITES_LOCAL, GuardedTool
from tribal_assistant.mcp.schemas import ActionOutcome, SyncOutcome
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.repositories.agent_settings import AgentSettingsRepository
from tribal_assistant.schemas.agents import AgentRunOut

VillageId = Annotated[int, Field(description="Own village id from get_overview.")]
DryRun = Annotated[bool, Field(description="true only simulates and logs; false acts in the game.")]
Reason = Annotated[str, Field(description="Why, in a few words (kept in the decision log).")]


class GameActionTools(ToolGroup):
    def __init__(self) -> None:
        self.operator = OperatorAgent()

    async def operate(self, village_id: int, tool: str, arguments: dict[str, Any], dry_run: bool) -> ActionOutcome:
        async def run(session: Any) -> ActionOutcome:
            contexts = await ContextLoader(session).load([village_id])
            if not contexts:
                raise NotFoundError(f"aldeia {village_id} não sincronizada: rode sync_account e veja get_overview")

            box = Toolbox(
                agent=self.operator,
                ctx=contexts[0],
                session=session,
                config=await AgentSettingsRepository(session).get(),
                run_id=f"mcp-{uuid4().hex[:8]}",
                dry_run=dry_run,
            )
            outcome = await box.invoke(tool, arguments)

            return ActionOutcome(ok=outcome.ok, dry_run=dry_run, detail=outcome.text, data=outcome.data)

        return await self.with_session(run)

    def register(self, mcp: MCPServer) -> None:
        @GuardedTool(mcp, annotations=REACHES_OUT)
        async def sync_account() -> SyncOutcome:
            """Log in if needed and read player, villages, troops, queues, commands and reports from the game."""
            from tribal_assistant.services.assistant import AssistantService

            result = await AssistantService().sync()
            return SyncOutcome(ok=result.ok, message=result.message)

        @GuardedTool(mcp, annotations=REACHES_OUT)
        async def run_agents(
            dry_run: DryRun = True,
            village_ids: Annotated[list[int] | None, Field(description="Only these villages; default all.")] = None,
        ) -> AgentRunOut:
            """Run every specialist (quests, strategy, economy, military, raids) once per village.

            Show the dry-run summaries to the user and get a yes before calling again with dry_run=false.
            """
            from dataclasses import asdict

            report = await AgentRunner(dry_run=dry_run, trigger="mcp").run(village_ids)
            return AgentRunOut.model_validate(asdict(report))

        @GuardedTool(mcp, annotations=REACHES_OUT)
        async def upgrade_building(
            village_id: VillageId,
            building: Annotated[str, Field(description="Building id: main, barracks, stable, garage, smith, snob, market, wood, stone, iron, farm, storage, hide, wall, statue, watchtower.")],
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Queue the next level of a building. Refused when the queue is full or resources, population or requirements are missing."""
            return await self.operate(village_id, "upgrade_building", {"building": building, "reason": reason}, dry_run)

        @GuardedTool(mcp, annotations=REACHES_OUT)
        async def recruit_units(
            village_id: VillageId,
            unit: Annotated[str, Field(description="spear, sword, axe, archer, spy, light, marcher, heavy, ram, catapult")],
            count: Annotated[int, Field(ge=1, description="Wanted amount; trimmed to the resource/population budget.")],
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Recruit troops within the resource reserve and recruit budget."""
            return await self.operate(village_id, "recruit_units", {"unit": unit, "count": count, "reason": reason}, dry_run)

        @GuardedTool(mcp, annotations=REACHES_OUT)
        async def send_farm_attack(
            village_id: VillageId,
            target: Annotated[str, Field(description="Barbarian village coordinates x|y.")],
            units: Annotated[dict[str, int], Field(description='Troops, e.g. {"light": 5} or {"spear": 10}.')],
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Loot a barbarian village. Refused for player villages, targets out of range or hit recently, and past the hourly limit.

            Confirm with the user before calling with dry_run=false: troops leave the village.
            """
            return await self.operate(
                village_id, "send_farm_attack", {"target": target, "units": units, "reason": reason}, dry_run
            )

        @GuardedTool(mcp, annotations=REACHES_OUT)
        async def claim_quest_rewards(village_id: VillageId, reason: Reason, dry_run: DryRun = True) -> ActionOutcome:
            """Claim every quest reward waiting; resources land in this village."""
            return await self.operate(village_id, "claim_quest_rewards", {"reason": reason}, dry_run)

        @GuardedTool(mcp, annotations=REACHES_OUT)
        async def complete_quest(
            village_id: VillageId,
            quest_id: Annotated[str, Field(description="Quest id from get_quests with can_complete=true.")],
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Hand in a quest whose goals are met."""
            return await self.operate(village_id, "complete_quest", {"quest_id": quest_id, "reason": reason}, dry_run)

        @GuardedTool(mcp, annotations=WRITES_LOCAL)
        async def set_village_goal(
            village_id: VillageId,
            goal: Annotated[str, Field(description="Goal in 1-3 sentences, with priorities.")],
        ) -> ActionOutcome:
            """Set the strategic goal the village agents follow from the next round on. Local only."""
            return await self.operate(village_id, "set_village_goal", {"goal": goal}, dry_run=False)
