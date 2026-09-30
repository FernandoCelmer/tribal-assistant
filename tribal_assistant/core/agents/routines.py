"""Routine work that needs no model and no coordinator: idle troops scavenge, the barracks never stands still."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.round import ProposerAgent
from tribal_assistant.core.agents.knobs import knob, knob_int, tuning
from tribal_assistant.core.agents.loader import ContextLoader
from tribal_assistant.core.agents.plan import PlanTracker
from tribal_assistant.core.agents.proposers.attack import SCAVENGERS, AttackProposer
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

    def box(self, ctx: VillageContext) -> Toolbox:
        box = Toolbox(agent=AGENT, ctx=ctx, session=self.session, config=self.config, run_id=self.run_id, dry_run=self.config.dry_run, actions=self.actions)
        box.brain_name = "routine"
        return box

    async def run(self) -> list[str]:
        done: list[str] = []
        for ctx in await ContextLoader(self.session).load():
            for step in (self.scavenge, self.research, self.recruit):
                try:
                    text = await step(ctx)
                except Exception as exc:
                    logger.warning("Rotina {} falhou na aldeia {}: {}", step.__name__, ctx.village.coords, exc)
                    continue
                if text:
                    done.append(f"[{ctx.village.coords}] {text}")
        return done

    @staticmethod
    def scavenge_plan(ctx: VillageContext) -> dict[int, dict[str, int]]:
        """Every idle scavenger home goes out, shared across the free tiers like the coordinator does."""
        if any(c.get("direction") == "in" for c in ctx.commands):
            return {}
        free = {o.option_id: o.loot_factor or 0.1 * o.option_id for o in ctx.village.scavenge if not o.is_locked and o.return_at is None}
        if not free:
            return {}
        keep = knob(ctx, "routine.scavenge_keep_share")
        units = {}
        for name in SCAVENGERS:
            unit = ctx.unit(name)
            count = int((unit.home if unit else 0) * (1 - keep))
            if count > 0:
                units[name] = count
        return AttackProposer.split(units, free, knob_int(ctx, "scavenge.min_pop")) if units else {}

    async def scavenge(self, ctx: VillageContext) -> str | None:
        parts = self.scavenge_plan(ctx)
        if not parts:
            return None
        box = self.box(ctx)
        sent = []
        for option, squad in parts.items():
            outcome = await box.invoke("send_scavenge", {"option_id": option, "units": squad, "reason": "rotina: tropas ociosas coletando"})
            if outcome.ok:
                sent.append(f"coleta {option}")
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
