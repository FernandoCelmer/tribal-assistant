"""Recruitment: troops the plan asks for, surplus into raiding troops, and the paladin."""

from tribal_assistant.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.agents.coordination.strategy import Role
from tribal_assistant.agents.coordination.view import CoordinationView
from tribal_assistant.agents.plan import PlanTracker
from tribal_assistant.agents.proposers.base import Proposer

BATCH = 25
MIN_BATCH = 5
FARM_UNITS = ("light", "spear", "axe")


class RecruitmentProposer(Proposer):
    key = "recruitment"
    title = "Recrutamento"
    observes = "tropas, população, filas e objetivo militar"
    delivers = "plano de produção de unidades"

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        items = []
        weight = {Role.OFFENSIVE: 0.7, Role.DEFENSE: 0.6, Role.SUPPORT: 0.65, Role.EMERGENCY: 0.5}.get(view.role, 0.4)

        for step in PlanTracker.next_recruits(ctx.plan)[:2]:
            unit = ctx.unit(step.target)
            if unit is None or not unit.available:
                continue

            queued = sum(r.count for r in ctx.village.recruit_orders if r.unit == step.target)
            count = min(BATCH, max(0, step.amount - unit.total - queued))
            plan = view.guard.plan_recruit(ctx, step.target, count)
            if count <= 0 or plan.refusal or plan.count < min(MIN_BATCH, count):
                continue

            items.append(self._recruit(view, step.target, plan.count, f"plano pede {step.amount} {step.target}", weight, purpose=f"plan:{step.target}"))

        research = await self._research(view)
        if research:
            items.append(research)

        storage = ctx.village.storage or 1
        if any(v >= storage * 0.85 for v in ctx.stock.values()):
            for unit in FARM_UNITS:
                plan = view.guard.plan_recruit(ctx, unit, BATCH)
                if not plan.refusal:
                    items.append(self._recruit(view, unit, plan.count, "armazém quase cheio: excedente em tropas de saque", weight * 0.8, opportunity=0.6))
                    break

        return items

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
        if ctx.levels.get("smith", 0) < 1 or view.dry_run or not await view.cooldown("smith", 1):
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
