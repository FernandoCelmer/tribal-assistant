"""Recruitment: troops the plan asks for, surplus into raiding troops, and the paladin."""

from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import Knobs, knob, knob_int, tuning
from tribal_assistant.core.agents.plan import PlanTracker
from tribal_assistant.core.agents.proposers.base import Proposer

FARM_UNITS = ("light", "spear", "axe")


class RecruitmentProposer(Proposer):
    key = "recruitment"
    title = "Recrutamento"
    observes = "tropas, população, filas e objetivo militar"
    delivers = "plano de produção de unidades"

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        items = []
        batch, min_batch = knob_int(view, "recruit.batch"), knob_int(view, "recruit.min_batch")
        weight = {Role.OFFENSIVE: 0.7, Role.DEFENSE: 0.6, Role.SUPPORT: 0.65, Role.EMERGENCY: 0.5}.get(view.role, 0.4)

        for step in PlanTracker.next_recruits(ctx.plan)[: knob_int(view, "plan.recruit_lookahead")]:
            unit = ctx.unit(step.target)
            if unit is None or not unit.available:
                continue

            queued = sum(r.count for r in ctx.village.recruit_orders if r.unit == step.target)
            count = min(batch, max(0, step.amount - unit.total - queued))
            plan = view.guard.plan_recruit(ctx, step.target, count)
            if count <= 0 or plan.refusal or plan.count < min(min_batch, count):
                continue

            items.append(self._recruit(view, step.target, plan.count, f"plano pede {step.amount} {step.target}", weight, purpose=f"plan:{step.target}"))

        research = await self._research(view)
        if research:
            items.append(research)

        spies = self._spies(view, weight)
        if spies:
            items.append(spies)

        scavenge = self._scavenge_army(view, weight)
        if scavenge:
            items.append(scavenge)

        storage = ctx.village.storage or 1
        if any(v >= storage * knob(view, "storage.near_full_share") for v in ctx.stock.values()):
            for unit in FARM_UNITS:
                plan = view.guard.plan_recruit(ctx, unit, batch)
                if not plan.refusal:
                    items.append(self._recruit(view, unit, plan.count, "armazém quase cheio: excedente em tropas de saque", weight * 0.8, opportunity=0.6))
                    break

        return items

    @staticmethod
    def scavenge_target(pop_max: int, share: float | None = None, knobs: Knobs | None = None) -> int:
        """Spears worth keeping for scavenging: they pay back in hours, so the army grows with the farm."""
        knobs = knobs or Knobs()
        share = share if share is not None else knobs.get("scavenge_share")
        return min(knobs.int("scavenge.cap"), int(pop_max * share))

    @staticmethod
    def spy_target(light: int, knobs: Knobs | None = None) -> int:
        """Scouts to keep: enough to probe every raid target, growing with the light cavalry."""
        knobs = knobs or Knobs()
        return max(knobs.int("spy.min"), light // knobs.int("spy.per_light"))

    def _spies(self, view: CoordinationView, weight: float) -> Proposal | None:
        ctx = view.ctx
        spy = ctx.unit("spy")
        if ctx.levels.get("stable", 0) < 1 or spy is None or not spy.available:
            return None

        light = ctx.unit("light")
        want = self.spy_target(light.total if light else 0, tuning(view))
        queued = sum(r.count for r in ctx.village.recruit_orders if r.unit == "spy")
        missing = want - spy.total - queued
        if missing <= 0:
            return None

        plan = view.guard.plan_recruit(ctx, "spy", missing)
        if plan.refusal or plan.count <= 0:
            return None

        return self._recruit(view, "spy", plan.count, f"exploradores para sondar alvos ({spy.total}/{want})", weight, opportunity=0.5, purpose="spy")

    def _scavenge_army(self, view: CoordinationView, weight: float) -> Proposal | None:
        ctx = view.ctx
        if view.role not in (Role.GROWTH, Role.EXPANSION) or not any(not o.is_locked for o in ctx.village.scavenge):
            return None

        spear = ctx.unit("spear")
        if spear is None or not spear.available:
            return None

        batch, min_batch = knob_int(view, "recruit.batch"), knob_int(view, "recruit.min_batch")
        queued = sum(r.count for r in ctx.village.recruit_orders if r.unit == "spear")
        target = self.scavenge_target(ctx.village.pop_max or 0, knobs=tuning(view))
        missing = target - spear.total - queued
        if missing < min_batch or queued >= batch * knob_int(view, "recruit.max_queued_batches"):
            return None

        plan = view.guard.plan_recruit(ctx, "spear", min(batch, missing))
        if plan.refusal or plan.count < min_batch:
            return None

        return self._recruit(view, "spear", plan.count, f"lanceiros para a coleta ({spear.total}/{target})", weight, opportunity=0.7, purpose="scavenge")

    def _recruit(self, view: CoordinationView, unit: str, count: int, reason: str, impact: float, opportunity: float = 0.3, purpose: str = "") -> Proposal:
        return Proposal(
            self.key,
            "recruit_units",
            {"unit": unit, "count": count, "reason": reason[:60]},
            reason,
            f"{count} {unit}",
            cost=view.unit_cost(unit, count),
            factors=Factors(urgency=0.2, impact=impact, opportunity=opportunity, opportunity_cost=0.3 if view.role == Role.GROWTH else 0.1),
            horizon=Horizon.TACTICAL,
            confidence=1.0,
            purpose=purpose,
            risks=["concorre com obras econômicas"],
        )

    RESEARCH_PRIORITY = ("light", "axe", "spy", "marcher", "heavy", "ram", "archer", "sword", "catapult")

    async def _research(self, view: CoordinationView) -> Proposal | None:
        ctx = view.ctx
        if ctx.levels.get("smith", 0) < 1 or view.dry_run or not await view.cooldown("smith"):
            return None

        techs = await view.actions.smith(ctx.game_id)
        ready = {t["unit"]: t for t in techs if t.get("level", 0) == 0 and not t.get("blocked")}
        unit = next((u for u in self.RESEARCH_PRIORITY if u in ready), None)
        if unit is None:
            return None

        cost = {k: v for k, v in ready[unit].get("cost", {}).items() if v}
        return Proposal(
            self.key,
            "research_unit",
            {"unit": unit, "reason": f"pesquisar {unit}"},
            f"{unit} liberado para pesquisa no ferreiro",
            f"permite recrutar {unit}",
            cost=cost,
            factors=Factors(urgency=0.3, impact=0.7 if unit in ("light", "axe") else 0.45, opportunity=0.5),
            horizon=Horizon.TACTICAL,
            confidence=0.8 if cost else 0.6,
            risks=[] if cost else ["custo só aparece na tela do ferreiro"],
        )
