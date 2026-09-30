"""Routine work that needs no model and no coordinator: idle troops scavenge, the barracks never stands still."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.policy import Policy
from tribal_assistant.core.agents.coordination.roles import RoleSelector
from tribal_assistant.core.agents.coordination.round import ProposerAgent, VillageRound
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import KnobStore, knob, knob_int, tuning
from tribal_assistant.core.agents.knowledge import UNITS
from tribal_assistant.core.agents.learning import LessonBook
from tribal_assistant.core.agents.loader import ContextLoader
from tribal_assistant.core.agents.plan import PlanTracker
from tribal_assistant.core.agents.proposers.attack import AttackProposer
from tribal_assistant.core.agents.proposers.recruitment import RecruitmentProposer
from tribal_assistant.core.agents.research import ResearchNeed
from tribal_assistant.core.agents.toolbox import Toolbox
from tribal_assistant.core.game.actions import GameActions
from tribal_assistant.core.schemas.agent_settings import AgentSettings

AGENT = ProposerAgent("routine", "Rotina")
RESOURCES = ("wood", "clay", "iron")
RAIDERS = ("axe", "light", "spear")


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Routines:
    def __init__(self, session: AsyncSession, config: AgentSettings, actions: GameActions | None = None) -> None:
        self.session = session
        self.config = config
        self.actions = actions or GameActions()
        self.run_id = f"routine-{uuid.uuid4().hex[:8]}"
        self.siblings: list[VillageContext] = []

    def box(self, ctx: VillageContext) -> Toolbox:
        box = Toolbox(agent=AGENT, ctx=ctx, session=self.session, config=self.config, run_id=self.run_id, dry_run=self.config.dry_run, actions=self.actions)
        box.brain_name = "routine"
        return box

    async def run(self) -> list[str]:
        done: list[str] = []
        contexts = await ContextLoader(self.session).load()
        self.siblings = contexts
        for ctx in contexts:
            for step in (self.troops, self.research, self.recruit):
                try:
                    text = await step(ctx)
                except Exception as exc:
                    logger.warning("Rotina {} falhou na aldeia {}: {}", step.__name__, ctx.village.coords, exc)
                    continue
                if text:
                    done.append(f"[{ctx.village.coords}] {text}")
        return done

    @staticmethod
    def troops_home(ctx: VillageContext) -> int:
        return sum(UNITS[u.name].pop * u.home for u in ctx.village.units if u.name in UNITS and u.name != "knight")

    async def view(self, ctx: VillageContext, siblings: list[VillageContext]) -> CoordinationView:
        knobs = await KnobStore(self.session).load()
        base, mode, _ = await RoleSelector(self.session, knobs).select(ctx, siblings)
        ctx.policy = Policy.for_role(mode.value, knobs)
        view = CoordinationView(ctx, self.session, self.config, self.actions, self.config.dry_run, mode, base, self.box(ctx))
        view.knobs = knobs
        view.siblings = siblings
        view.recent = await VillageRound(self.session, self.config, self.run_id, self.config.dry_run, self.actions)._recent(ctx, knobs.int("coordinator.recent_minutes"))
        return view

    async def troops(self, ctx: VillageContext) -> str | None:
        """Troops home go out at once: trusted raids and probes first, the rest scavenging, the same plan the attack specialist makes."""
        if any(c.get("direction") == "in" for c in ctx.commands):
            return None
        if self.troops_home(ctx) < knob_int(ctx, "scavenge.min_pop"):
            return None
        book = LessonBook(self.session)
        pause = f"routine_troops:{ctx.game_id}"
        if not await book.due(pause, knob(ctx, "routine.troops_retry_minutes") / 60):
            return None

        view = await self.view(ctx, self.siblings)
        least = knob(view, "raid.min_confidence")
        box = self.box(ctx)
        sent = []
        for proposal in await AttackProposer().propose(view):
            if proposal.key in view.recent or (proposal.action != "send_scavenge" and proposal.confidence < least):
                continue
            outcome = await box.invoke(proposal.action, proposal.arguments)
            if outcome.ok:
                sent.append(proposal.title())
        if not sent:
            await book.mark(pause, "nada para enviar")
        return ", ".join(sent) or None

    @staticmethod
    def queue_minutes(ctx: VillageContext) -> float:
        ends = [o.finishes_at for o in ctx.village.recruit_orders if o.finishes_at]
        if not ends:
            return 0.0
        latest = max(e.replace(tzinfo=None) if e.tzinfo is None else e.astimezone(UTC).replace(tzinfo=None) for e in ends)
        return max(0.0, (latest - _now()).total_seconds() / 60)

    @staticmethod
    def recruit_unit(ctx: VillageContext) -> str | None:
        """The plan's next unit, else spears for scavenging until the target, else the best raider the village can train."""
        for step in PlanTracker.next_recruits(ctx.plan):
            unit = ctx.unit(step.target)
            if unit is not None and unit.available and step.amount > unit.total:
                return step.target
        spear = ctx.unit("spear")
        target = RecruitmentProposer.scavenge_target(ctx.village.pop_max or 0, knobs=tuning(ctx))
        if spear is not None and spear.available and spear.total < target:
            return "spear"
        return next((name for name in RAIDERS if (u := ctx.unit(name)) is not None and u.available), None)

    @staticmethod
    def recruit_count(ctx: VillageContext, unit: Any) -> int:
        """A small batch paid from a tuned share of each resource, so big plans keep saving while the barracks keeps going."""
        share = knob(ctx, "routine.recruit_share")
        costs = {"wood": unit.cost_wood or 0, "clay": unit.cost_clay or 0, "iron": unit.cost_iron or 0}
        limits = [int(ctx.stock.get(r, 0) * share // cost) for r, cost in costs.items() if cost]
        pop = unit.cost_pop or 1
        limits.append(ctx.pop_free // pop)
        limits.append(knob_int(ctx, "recruit.batch"))
        return max(0, min(limits)) if limits else 0

    async def recruit(self, ctx: VillageContext) -> str | None:
        if any(c.get("direction") == "in" for c in ctx.commands):
            return None
        if self.queue_minutes(ctx) >= knob(ctx, "routine.recruit_queue_minutes"):
            return None
        name = self.recruit_unit(ctx)
        unit = ctx.unit(name) if name else None
        if unit is None:
            return None
        count = self.recruit_count(ctx, unit)
        if count < knob_int(ctx, "recruit.min_batch"):
            return None
        outcome = await self.box(ctx).invoke("recruit_units", {"unit": name, "count": count, "reason": "rotina: quartel sem parar"})
        return f"recrutou {count} {name}" if outcome.ok else None

    async def research(self, ctx: VillageContext) -> str | None:
        """Starts the next smithy research as soon as its cost is in stock; reads the smithy again when the need is old."""
        if ctx.levels.get("smith", 0) < 1:
            return None
        needs = ResearchNeed(self.session, ctx.game_id)
        row = await needs.row()
        stale = row is None or _now() - row.last_seen > timedelta(hours=knob(ctx, "cooldown.smith"))
        if stale:
            techs = await self.actions.smith(ctx.game_id)
            if any(t.get("busy") for t in techs):
                await needs.save(None, {})
                return None
            ready = {t["unit"]: t for t in techs if t.get("level", 0) == 0 and not t.get("blocked")}
            unit = next((u for u in RecruitmentProposer.RESEARCH_PRIORITY if u in ready), None)
            cost = {k: v for k, v in (ready[unit].get("cost", {}) if unit else {}).items() if v}
            await needs.save(unit, cost)
            need = {"unit": unit, "cost": cost}
        else:
            need = await needs.get()

        unit, cost = need.get("unit"), need.get("cost") or {}
        if not unit or not cost or any(ctx.stock.get(r, 0) < int(v) for r, v in cost.items() if r in RESOURCES):
            return None
        outcome = await self.box(ctx).invoke("research_unit", {"unit": unit, "reason": "rotina: pesquisa com recurso disponível"})
        if outcome.ok:
            return f"pesquisa de {unit}"
        return None
