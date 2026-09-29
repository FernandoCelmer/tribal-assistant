"""Read-only account state: overview, quests, agent log, configuration, game knowledge."""

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from tribal_assistant.agents.knowledge import GameKnowledge
from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.mcp.annotations import READ_ONLY, WRITES_LOCAL, GuardedTool
from tribal_assistant.mcp.schemas import Decisions, Knowledge, Plans
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.schemas.agent_settings import AgentSettings, AgentSettingsUpdate
from tribal_assistant.schemas.agents import AgentConfigOut, AgentDecisionOut, QuestsOut
from tribal_assistant.schemas.game import GameOverview
from tribal_assistant.services.agents import AgentService
from tribal_assistant.services.game import GameService


class StateTools(ToolGroup):
    def register(self, mcp: MCPServer) -> None:
        @GuardedTool(mcp, annotations=READ_ONLY)
        async def get_overview() -> GameOverview:
            """Player, every own village (resources, buildings with next-level cost, troops, queues,
            scavenging, advisor recommendations), troop movements and recent reports, as last synced.

            Call sync_account first when the data may be stale.
            """
            return await self.with_session(lambda s: GameService(s).overview())

        @GuardedTool(mcp, annotations=READ_ONLY)
        async def get_quests() -> QuestsOut:
            """Active quests with goals and progress, plus rewards waiting to be claimed (as of the last agent round)."""
            return await self.with_session(lambda s: AgentService(s).quests())

        @GuardedTool(mcp, annotations=READ_ONLY)
        async def get_agent_decisions(
            limit: Annotated[int, Field(ge=1, le=500, description="How many decisions, newest first.")] = 30,
            village_id: Annotated[int | None, Field(description="Only this village (id from get_overview).")] = None,
        ) -> Decisions:
            """What the village agents did, why, and what the game answered."""
            rows: list[AgentDecisionOut] = await self.with_session(
                lambda s: AgentService(s).decisions(village_id, limit)
            )
            return Decisions(decisions=rows)

        @GuardedTool(mcp, annotations=READ_ONLY)
        async def get_plans() -> Plans:
            """Each village's plan: ordered steps with live status (pending, queued, done, blocked) and progress."""
            rows = await self.with_session(lambda s: AgentService(s).plans())
            return Plans(plans=rows)

        @GuardedTool(mcp, annotations=READ_ONLY)
        async def get_agents_config() -> AgentConfigOut:
            """Agent brain (LLM provider/model or rules) and the runtime settings: schedule, dry-run and guardrail limits."""
            return await self.with_session(lambda s: AgentService(s).config())

        @GuardedTool(mcp, annotations=WRITES_LOCAL)
        async def update_agent_settings(
            enabled: Annotated[bool | None, Field(description="Run agents on the server schedule.")] = None,
            interval_minutes: Annotated[int | None, Field(ge=1, le=1440, description="Minutes between rounds.")] = None,
            dry_run: Annotated[bool | None, Field(description="Simulate instead of acting.")] = None,
            resource_reserve: Annotated[float | None, Field(ge=0, le=0.9, description="Share of storage kept untouched.")] = None,
            recruit_budget: Annotated[float | None, Field(ge=0, le=1, description="Share of spare resources recruiting may spend.")] = None,
            max_attacks_per_hour: Annotated[int | None, Field(ge=0, le=200, description="Attacks per village per hour.")] = None,
            attack_radius: Annotated[int | None, Field(ge=1, le=50, description="Max distance to barbarian targets.")] = None,
            retarget_minutes: Annotated[int | None, Field(ge=0, le=1440, description="Minutes before re-hitting a target.")] = None,
            build_queue_slots: Annotated[int | None, Field(ge=1, le=5, description="Build orders agents may keep queued.")] = None,
            llm_agents: Annotated[list[str] | None, Field(description="Agents allowed to call the AI: strategist, economist, commander, quartermaster, raider.")] = None,
            plan_refresh_hours: Annotated[int | None, Field(ge=1, le=168, description="Hours before the plan is rewritten.")] = None,
            auto_finish_free: Annotated[bool | None, Field(description="Use the free finish-now button on short builds.")] = None,
        ) -> AgentSettings:
            """Change agent settings at runtime. Only the given fields change. Confirm with the user before enabling or leaving dry-run."""
            patch = AgentSettingsUpdate(
                enabled=enabled,
                interval_minutes=interval_minutes,
                dry_run=dry_run,
                resource_reserve=resource_reserve,
                recruit_budget=recruit_budget,
                max_attacks_per_hour=max_attacks_per_hour,
                attack_radius=attack_radius,
                retarget_minutes=retarget_minutes,
                build_queue_slots=build_queue_slots,
                auto_finish_free=auto_finish_free,
                llm_agents=llm_agents,
                plan_refresh_hours=plan_refresh_hours,
            )
            return await self.with_session(lambda s: AgentService(s).update_settings(patch))

        @GuardedTool(mcp, annotations=READ_ONLY)
        async def lookup_knowledge(
            kind: Annotated[Literal["building", "unit", "strategy"], Field(description="What to look up.")],
            id: Annotated[str, Field(description="Building id (main, barracks, snob...) or unit id (spear, light...); ignored for strategy.")] = "",
        ) -> Knowledge:
            """Documented game facts: building requirements and max level, unit cost/speed/carry, base strategy."""
            if kind == "strategy":
                return Knowledge(strategy=GameKnowledge.strategy)

            info = GameKnowledge.building(id) if kind == "building" else GameKnowledge.unit(id)
            if info is None:
                raise NotFoundError(f"{kind} {id!r} desconhecido: use ids como main, barracks, spear, light")

            return Knowledge(**info)
