"""Read-only account state: overview, quests, agent log, configuration, game knowledge."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from tribal_assistant.mcp.annotations import READ_ONLY, REPLACES_LOCAL, GuardedTool
from tribal_assistant.mcp.schemas import Coordination, Decisions, Knowledge, Plans, VillageState
from tribal_assistant.mcp.tools.base import ToolGroup


class StateTools(ToolGroup):
    def register(self, mcp: MCPServer) -> None:
        @GuardedTool(mcp, title="Account overview", annotations=READ_ONLY)
        async def get_overview() -> dict[str, Any]:
            """Full account snapshot as last synced: player (points, rank, incomings, daily_bonus
            waiting, beginner protection_until; premium_points is informational, never spent), every
            own village with its id, coords, resources, storage, population, production, buildings
            (level, next-level cost and whether it can be built), troops (home, away, recruitable),
            build and recruit queues, scavenging tiers, troop movements (incoming attacks first) and
            recent reports.

            Source of the village ids every other tool takes. Large: for one village prefer
            get_village_state. Data is as fresh as the last sync_account.
            """
            return await self.api.get("/game/overview")

        @GuardedTool(mcp, title="Village state", annotations=READ_ONLY)
        async def get_village_state(
            village_id: Annotated[int, Field(description="Own village id from get_overview.")],
        ) -> VillageState:
            """Compact pt-BR summary of one village: resources and production, population, build
            queue and free slots, buildings with next cost and whether they can be built (or what
            blocks them), troops home/away/recruitable, scavenging tiers, quests, the plan with
            step status, incoming attacks and the goal.

            The same view the agents reason on; a few hundred tokens instead of get_overview's
            thousands. Use it before proposing actions for one village.
            """
            outcome = await self.api.post(
                "/agents/act", {"village_id": village_id, "tool": "get_village_state", "arguments": {}, "dry_run": True, "source": "mcp"}
            )
            return VillageState(village_id=village_id, state=outcome["detail"])

        @GuardedTool(mcp, title="Quests", annotations=READ_ONLY)
        async def get_quests() -> dict[str, Any]:
            """Active quests with each goal's progress (current/target) and can_complete, plus the
            rewards waiting to be claimed. Refreshed on every agent round.

            Quests pay resources: hand in can_complete ones with complete_quest, then
            claim_quest_rewards. Building goals ("Expanda Bosque ao nível 5") are good plan steps.
            """
            return await self.api.get("/agents/quests")

        @GuardedTool(mcp, title="Agent decisions", annotations=READ_ONLY)
        async def get_agent_decisions(
            limit: Annotated[int, Field(ge=1, le=500, description="How many decisions, newest first.")] = 30,
            village_id: Annotated[int | None, Field(description="Only this own village id from get_overview; omit for all.")] = None,
        ) -> Decisions:
            """Decision log: every action an agent or MCP call tried, with arguments, reason, dry_run,
            ok and what the game (or the guardrails, as RECUSADO) answered. Use it after run_agents
            or a live action to report results, and to explain why something did not happen.
            """
            return Decisions(decisions=await self.api.get("/agents/decisions", village_id=village_id, limit=limit))

        @GuardedTool(mcp, title="Village plans", annotations=READ_ONLY)
        async def get_plans() -> Plans:
            """Each village's plan: summary, who wrote it (llm, rules or mcp), when, and the ordered
            steps with live status (pending, queued, done, blocked plus the blocking reason) and
            done/total. Read it before set_village_plan, which replaces it.
            """
            return Plans(plans=await self.api.get("/agents/plans"))

        @GuardedTool(mcp, title="Coordinator decisions", annotations=READ_ONLY)
        async def get_coordination() -> Coordination:
            """What the coordinator decided in the last round for each village: role and mode (growth,
            defense, offensive, support, expansion, emergency), next best action with reason, cost and
            confidence, what was executed, what was deferred and why (reserved resources, vetoes,
            missing resources with ETA, waiting approval), reservations, vetoes and labelled insights
            (fact, estimate, hypothesis). Read this first to explain why something was or was not done.
            """
            return Coordination(villages=await self.api.get("/agents/coordination"))

        @GuardedTool(mcp, title="Set village role", annotations=REPLACES_LOCAL)
        async def set_village_role(
            village_id: Annotated[int, Field(description="Own village id from get_overview.")],
            role: Annotated[
                Literal["growth", "defense", "offensive", "support", "expansion"] | None,
                Field(description="Fixed role; null returns the choice to the coordinator."),
            ] = None,
            reason: Annotated[str, Field(max_length=200, description="Why, in a few words.")] = "",
        ) -> dict[str, Any]:
            """Fix the strategic role of a village (the coordinator's priority weights follow it), or pass
            null to let the coordinator choose again. An incoming attack still forces emergency mode.
            Ask the user before changing it.
            """
            return await self.api.put(f"/agents/villages/{village_id}/role", {"role": role, "reason": reason})

        @GuardedTool(mcp, title="Agent configuration", annotations=READ_ONLY)
        async def get_agents_config() -> dict[str, Any]:
            """How the agents decide and what limits them: brain (LLM provider and model, or rules),
            which agents may call the AI, schedule (enabled, interval), global dry-run, and the
            and each village's current limits come from its role (see get_coordination).
            """
            return await self.api.get("/agents/config")

        @GuardedTool(mcp, title="Update agent settings", annotations=REPLACES_LOCAL)
        async def update_agent_settings(
            enabled: Annotated[bool | None, Field(description="Run agents on the server schedule.")] = None,
            interval_minutes: Annotated[int | None, Field(ge=1, le=1440, description="Minutes between rounds.")] = None,
            dry_run: Annotated[bool | None, Field(description="Simulate instead of acting.")] = None,
            llm_agents: Annotated[list[str] | None, Field(description="Agents allowed to call the AI: strategist.")] = None,
            plan_refresh_minutes: Annotated[int | None, Field(ge=5, le=10080, description="Minutes before the plan is rewritten.")] = None,
            auto_finish_free: Annotated[bool | None, Field(description="Use the free finish-now button on short builds.")] = None,
        ) -> dict[str, Any]:
            """Change agent settings at runtime; only the fields given change, the rest keep their
            value. Returns the full settings after the change.

            enabled=true makes the server act on its own every interval_minutes, and dry_run=false
            makes those rounds real: confirm both with the user first. Reserves, recruit budget,
            attack radius and pace are decided by the coordinator from each village role.
            """
            patch = {
                "enabled": enabled,
                "interval_minutes": interval_minutes,
                "dry_run": dry_run,
                "auto_finish_free": auto_finish_free,
                "llm_agents": llm_agents,
                "plan_refresh_minutes": plan_refresh_minutes,
            }
            return await self.api.patch("/agents/settings", {k: v for k, v in patch.items() if v is not None})

        @GuardedTool(mcp, title="Game knowledge", annotations=READ_ONLY)
        async def lookup_knowledge(
            kind: Annotated[Literal["building", "unit", "strategy", "guide"], Field(description="building, unit, strategy for the base playbook, or guide for a full pt-BR guide.")],
            id: Annotated[str, Field(description="Building id or pt-BR name (main, barracks, snob, 'Academia'...) or unit id (spear, light, snob...); inicio, avancado or nobre for guide; ignored for strategy.")] = "",
        ) -> Knowledge:
            """Facts from the official pt-BR help pages. building: label, max_level, requires
            (building -> level) and role. unit: cost, pop, attack, defense (general/cavalry/archer),
            minutes_per_field, carry and research requirement. strategy: the base playbook the
            agents follow. guide: a full guide (inicio = first days, avancado = many villages and
            tribe, nobre = conquest). World settings can differ; the game's own answer is final.
            """
            if kind == "strategy":
                return Knowledge(strategy=await self.api.get("/knowledge/strategy"))

            if kind == "guide":
                return Knowledge(guide=id, text=await self.api.get(f"/knowledge/guides/{id}"))

            return Knowledge(**await self.api.get(f"/knowledge/{kind}s/{id}"))
