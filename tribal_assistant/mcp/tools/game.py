"""Actions in the live game. All pass the agent guardrails and are logged; dry_run defaults to true."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from tribal_assistant.agents.runner import AgentRunner
from tribal_assistant.mcp.annotations import (
    DESTRUCTIVE,
    REACHES_OUT,
    READS_GAME,
    REPLACES_LOCAL,
    GuardedTool,
)
from tribal_assistant.mcp.schemas import ActionOutcome, PlanStepIn, SyncOutcome
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.mcp.tools.bridge import ToolboxBridge
from tribal_assistant.schemas.agents import AgentRunOut

VillageId = Annotated[int, Field(description="Own village id (the `id` field of a village in get_overview), not its coordinates.")]
DryRun = Annotated[bool, Field(description="true (default) only simulates and logs the decision; false acts in the game. Use false only after the user said yes to the dry run.")]
Reason = Annotated[str, Field(min_length=1, max_length=200, description="Why, in a few words; stored in the decision log (e.g. 'quest: Bosque 5').")]
Troops = Annotated[
    dict[str, Annotated[int, Field(ge=1)]],
    Field(min_length=1, description='Troops by unit id, e.g. {"light": 5} or {"spear": 10, "axe": 5}. Only troops at home count.'),
]
Tier = Annotated[int, Field(ge=1, le=4, description="Scavenging tier: 1 Pequena, 2 Média, 3 Grande, 4 Extrema.")]
Building = Literal[
    "main", "barracks", "stable", "garage", "church", "smith", "snob", "market", "wood", "stone",
    "iron", "farm", "storage", "hide", "wall", "statue", "watchtower", "place",
]
Unit = Literal["spear", "sword", "axe", "archer", "spy", "light", "marcher", "heavy", "ram", "catapult"]


class GameActionTools(ToolGroup):
    def __init__(self) -> None:
        self.bridge = ToolboxBridge()

    async def operate(self, village_id: int, tool: str, arguments: dict[str, Any], dry_run: bool) -> ActionOutcome:
        outcome = await self.bridge.invoke(village_id, tool, arguments, dry_run)
        return ActionOutcome(ok=outcome.ok, dry_run=dry_run, detail=outcome.text, data=outcome.data)

    def register(self, mcp: MCPServer) -> None:
        @GuardedTool(mcp, title="Sync account", annotations=READS_GAME)
        async def sync_account() -> SyncOutcome:
            """Refresh the local copy of the account from the live game.

            Logs in if the browser session expired, then reads the player, every own village
            (resources, buildings, troops, build and recruit queues, scavenging), troop movements,
            reports and quests. Changes nothing in the game. Takes tens of seconds and opens real
            pages, so call it once at the start of a session or after acting, not before every read.
            """
            from tribal_assistant.services.assistant import AssistantService

            result = await AssistantService().sync()
            return SyncOutcome(ok=result.ok, message=result.message)

        @GuardedTool(mcp, title="Run village agents", annotations=DESTRUCTIVE)
        async def run_agents(
            dry_run: DryRun = True,
            village_ids: Annotated[list[int] | None, Field(description="Only these own village ids; omit for every village.")] = None,
        ) -> AgentRunOut:
            """Run one full round of the specialists on each village, in order: quartermaster (quests,
            rewards, daily bonus), strategist (plan), economist (economy builds, scavenging unlocks),
            commander (military builds, recruiting) and raider (barbarian loot, scavenging).

            Uses the configured brain (LLM or rules) and the guardrails; every decision is logged
            (see get_agent_decisions). A live round spends resources and sends troops, so run it with
            dry_run=true first, show the per-village summaries, and repeat with dry_run=false only
            after the user agrees. Needs a synced account (sync_account); a live round that acted
            re-syncs on its own.
            """
            from dataclasses import asdict

            report = await AgentRunner(dry_run=dry_run, trigger="mcp").run(village_ids)
            return AgentRunOut.model_validate(asdict(report))

        @GuardedTool(mcp, title="Upgrade building", annotations=REACHES_OUT)
        async def upgrade_building(
            village_id: VillageId,
            building: Annotated[Building, Field(description="Building id. snob is the Academy; church only exists on church worlds.")],
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Queue the next level of one building (one level per call).

            Refused with RECUSADO when the building is already queued, the build queue is full
            (2 without premium), the building is at max level, documented requirements are missing
            (e.g. Academy needs Headquarters 20, Smithy 20, Market 10), resources or free population
            are short. Costs come from get_overview (next_wood/next_clay/next_iron/next_pop).
            data.level is the level queued. Never spends premium points.
            """
            return await self.operate(village_id, "upgrade_building", {"building": building, "reason": reason}, dry_run)

        @GuardedTool(mcp, title="Recruit units", annotations=REACHES_OUT)
        async def recruit_units(
            village_id: VillageId,
            unit: Annotated[Unit, Field(description="Unit id. light/marcher/heavy/spy need the Stable, ram/catapult the Workshop, others the Barracks.")],
            count: Annotated[int, Field(ge=1, le=10_000, description="Wanted amount; trimmed down to the budget, never raised.")],
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Recruit troops in this village.

            The count is trimmed to what the budget allows: stock above the resource reserve times
            the role's recruit budget, free population and the game's own
            maximum. Refused when the unit is not researched or no budget is left. data.count is the
            amount actually ordered.
            """
            return await self.operate(village_id, "recruit_units", {"unit": unit, "count": count, "reason": reason}, dry_run)

        @GuardedTool(mcp, title="Send farm attack", annotations=DESTRUCTIVE)
        async def send_farm_attack(
            village_id: VillageId,
            target: Annotated[str, Field(pattern=r"^\d{1,3}\|\d{1,3}$", description="Barbarian village coordinates x|y, from list_barbarians or list_nearby kind=barbarian.")],
            units: Troops,
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Send a looting attack to a barbarian village.

            Refused for player villages or targets not known as barbarian, targets beyond
            the role's attack radius, targets hit recently, troops not at home, and after
            the role's hourly attack limit. Troops can die: prefer 5 light cavalry or 10
            spearmen on low-point barbarians. data.arrival is the arrival time. Confirm with the
            user before dry_run=false: troops leave the village.
            """
            return await self.operate(
                village_id, "send_farm_attack", {"target": target, "units": units, "reason": reason}, dry_run
            )

        @GuardedTool(mcp, title="Send scavenging", annotations=REACHES_OUT)
        async def send_scavenge(
            village_id: VillageId,
            option_id: Tier,
            units: Troops,
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Send troops to scavenge resources on one unlocked, idle tier. No troops are lost,
            but they cannot be recalled until the run ends.

            Refused when the tier is locked or already running, troops are not at home, or an
            attack is incoming (troops stay home to defend). Use the highest idle tier and keep
            the troops the raider needs for looting. Tier state is in get_village_state.
            """
            return await self.operate(
                village_id, "send_scavenge", {"option_id": option_id, "units": units, "reason": reason}, dry_run
            )

        @GuardedTool(mcp, title="Unlock scavenging tier", annotations=REACHES_OUT)
        async def unlock_scavenge(
            village_id: VillageId,
            option_id: Tier,
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Start unlocking the next scavenging tier at the rally point. Costs resources and takes time.

            Tiers unlock in order (1 before 2...), one at a time. Refused when the tier is already
            unlocked or unlocking, another tier is unlocking, or the previous tier is still locked.
            Scavenging yields resources without risking troops, so it pays off early.
            """
            return await self.operate(village_id, "unlock_scavenge", {"option_id": option_id, "reason": reason}, dry_run)

        @GuardedTool(mcp, title="Claim quest rewards", annotations=REACHES_OUT)
        async def claim_quest_rewards(village_id: VillageId, reason: Reason, dry_run: DryRun = True) -> ActionOutcome:
            """Claim every quest reward waiting (count in get_quests.rewards); the resources land in
            this village, so pick the one with the most free storage. Answers ok=false when nothing
            is waiting.
            """
            return await self.operate(village_id, "claim_quest_rewards", {"reason": reason}, dry_run)

        @GuardedTool(mcp, title="Complete quest", annotations=REACHES_OUT)
        async def complete_quest(
            village_id: VillageId,
            quest_id: Annotated[str, Field(min_length=1, description="quest_id from get_quests whose can_complete is true.")],
            reason: Reason,
            dry_run: DryRun = True,
        ) -> ActionOutcome:
            """Hand in one quest whose goals are all met (the "Missão completa" button). Then call
            claim_quest_rewards to collect what it gave. Refused when the quest is unknown or its
            goals are not met yet.
            """
            return await self.operate(village_id, "complete_quest", {"quest_id": quest_id, "reason": reason}, dry_run)

        @GuardedTool(mcp, title="Open daily bonus", annotations=REACHES_OUT)
        async def open_daily_bonus(village_id: VillageId, reason: Reason, dry_run: DryRun = True) -> ActionOutcome:
            """Open the free daily-bonus chests on the profile; items go to the inventory.

            Account-wide, so any own village id works. Checked at most once every 4 hours; a
            second call inside that window answers ok=false. Never uses premium points.
            """
            return await self.operate(village_id, "open_daily_bonus", {"reason": reason}, dry_run)

        @GuardedTool(mcp, title="Set village goal", annotations=REPLACES_LOCAL)
        async def set_village_goal(
            village_id: VillageId,
            goal: Annotated[str, Field(min_length=1, max_length=500, description="Goal in 1-3 sentences with priorities, e.g. 'Academia: EP 20, Ferreiro 20, Mercado 10; armazém nunca cheio'.")],
        ) -> ActionOutcome:
            """Replace the village's strategic goal. The agents read it every round and the
            strategist plans around it. Local only: nothing is sent to the game, no dry run.
            """
            return await self.operate(village_id, "set_village_goal", {"goal": goal}, dry_run=False)

        @GuardedTool(mcp, title="Set village plan", annotations=REPLACES_LOCAL)
        async def set_village_plan(
            village_id: VillageId,
            summary: Annotated[str, Field(min_length=1, max_length=500, description="Strategy in 1-3 sentences.")],
            steps: Annotated[list[PlanStepIn], Field(min_length=1, max_length=12, description="Up to 12 steps, most important first.")],
        ) -> ActionOutcome:
            """Replace the village plan: ordered steps the economist and commander execute on their own,
            without AI, from the next round on.

            Steps with unknown ids or out-of-range amounts are dropped and listed in detail. Build
            steps name the level to reach (not +1), recruit steps the total troops to own. Read the
            current plan with get_plans first; this overwrites it. Local only, no dry run.
            """
            payload = {"summary": summary, "steps": [s.model_dump() for s in steps]}
            return await self.operate(village_id, "set_village_plan", payload, dry_run=False)
