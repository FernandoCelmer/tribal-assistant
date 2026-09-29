"""Recruitment: troops the plan asks for, surplus into raiding troops, and the paladin."""

from tribal_assistant.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.agents.coordination.strategy import Role
from tribal_assistant.agents.coordination.view import CoordinationView
from tribal_assistant.agents.plan import PlanTracker
from tribal_assistant.agents.proposers.base import Proposer

BATCH = 25
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
            if count <= 0 or plan.refusal:
                continue

            items.append(self._recruit(view, step.target, plan.count, f"plano pede {step.amount} {step.target}", weight, purpose=f"plan:{step.target}"))

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
