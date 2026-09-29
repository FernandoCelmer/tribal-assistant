"""Defense: incoming attacks become vetoes, reservations and urgent defensive proposals."""

from datetime import timedelta

from tribal_assistant.core.agents.coordination.budget import Reservation
from tribal_assistant.core.agents.coordination.constraints import Constraint
from tribal_assistant.core.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.proposers.base import Proposer, clamp

DEFENDERS = ("spear", "sword", "archer", "heavy")
SPEND_BLOCKED = ("train_knight", "accept_market_offer", "use_item")


class DefenseProposer(Proposer):
    key = "defense"
    title = "Defesa"
    observes = "ataques recebidos, tropas e tempo até o impacto"
    delivers = "alertas, vetos temporários e opções de resposta"

    def _threat(self, view: CoordinationView) -> float | None:
        return view.estimator.hours_to_impact()

    async def constraints(self, view: CoordinationView) -> list[Constraint]:
        hours = self._threat(view)
        if hours is None:
            return []

        until = now() + timedelta(hours=hours + 0.25)
        view.note(Insight("threat", f"ataque chega em {hours:.1f}h; tamanho desconhecido", Certainty.HYPOTHESIS, now(), 0.5, hours, self.key))
        return [
            Constraint("hold_troops", "ataque chegando: tropas ficam em casa até o impacto", self.key, until),
            Constraint("block_actions", "ataque chegando: não gastar com paladino, mercado ou itens", self.key, until, SPEND_BLOCKED),
        ]

    async def reservations(self, view: CoordinationView) -> list[Reservation]:
        hours = self._threat(view)
        if hours is None:
            return []

        home = {u.name: u.home for u in view.ctx.village.units if u.name in DEFENDERS and u.home}
        wall = view.build_cost("wall")
        return [
            Reservation(
                "defense",
                "defense",
                f"resposta ao ataque em {hours:.1f}h: muralha e defensores",
                {k: v for k, v in wall.items() if k != "pop"},
                home,
            )
        ]

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        hours = self._threat(view)
        if hours is None:
            return self._prepare(view)

        urgency = clamp(1 - hours / 6)
        items = []

        if not view.guard.check_upgrade(view.ctx, "wall"):
            items.append(
                Proposal(
                    self.key,
                    "upgrade_building",
                    {"building": "wall", "reason": "ataque chegando: muralha"},
                    f"ataque em {hours:.1f}h",
                    "muralha multiplica a defesa",
                    cost=view.build_cost("wall"),
                    factors=Factors(urgency=urgency, impact=0.5, risk_avoided=0.9),
                    horizon=Horizon.IMMEDIATE,
                    deadline=now() + timedelta(hours=hours),
                    confidence=0.9,
                    purpose="defense",
                    key="upgrade_building:wall",
                )
            )

        for unit in ("spear", "sword"):
            plan = view.guard.plan_recruit(view.ctx, unit, 20)
            if plan.refusal:
                continue

            items.append(
                Proposal(
                    self.key,
                    "recruit_units",
                    {"unit": unit, "count": plan.count, "reason": "ataque chegando: defensores"},
                    f"ataque em {hours:.1f}h",
                    "mais defesa em casa",
                    cost=view.unit_cost(unit, plan.count),
                    factors=Factors(urgency=urgency, impact=0.4, risk_avoided=0.8),
                    horizon=Horizon.IMMEDIATE,
                    deadline=now() + timedelta(hours=hours),
                    confidence=0.7,
                    purpose="defense",
                    risks=["tropas podem não ficar prontas antes do impacto"],
                )
            )
            break

        return items

    WALL_TARGET = 5
    HIDE_TARGET = 3
    SPEAR_TARGET = 60

    def _prepare(self, view: CoordinationView) -> list[Proposal]:
        """Before beginner protection ends, or in defense role: wall, hiding place and spearmen."""
        from tribal_assistant.core.agents.coordination.roles import (
            PROTECTION_WARNING_HOURS,
            RoleSelector,
        )
        from tribal_assistant.core.agents.coordination.strategy import Role

        ctx = view.ctx
        protection = RoleSelector.protection_hours(ctx)
        ending = protection is not None and 0 < protection <= PROTECTION_WARNING_HOURS
        if not ending and view.role != Role.DEFENSE:
            return []

        why = f"proteção de iniciante acaba em {protection:.0f}h" if ending else "papel defesa"
        urgency = clamp(1 - (protection or 12) / PROTECTION_WARNING_HOURS) if ending else 0.4
        deadline = now() + timedelta(hours=protection) if ending else None
        view.note(Insight("protection", f"{why}: preparar muralha, esconderijo e lanceiros", Certainty.FACT, now(), 1.0, protection, self.key))

        items = []
        for building, target, impact in (("wall", self.WALL_TARGET, 0.6), ("hide", self.HIDE_TARGET, 0.4)):
            refusal = view.guard.check_upgrade(ctx, building) or ""
            if ctx.levels.get(building, 0) >= target or (refusal and "recurso" not in refusal and "população" not in refusal):
                continue

            items.append(
                Proposal(
                    self.key,
                    "upgrade_building",
                    {"building": building, "reason": f"{why}: {building}"},
                    why,
                    "muralha multiplica a defesa" if building == "wall" else "esconderijo protege recursos do saque",
                    cost=view.build_cost(building),
                    factors=Factors(urgency=urgency, impact=impact, risk_avoided=0.7),
                    horizon=Horizon.TACTICAL,
                    deadline=deadline,
                    confidence=0.85,
                    key=f"upgrade_building:{building}",
                )
            )

        spear = ctx.unit("spear")
        if spear and spear.available and spear.total < self.SPEAR_TARGET:
            plan = view.guard.plan_recruit(ctx, "spear", min(20, self.SPEAR_TARGET - spear.total))
            if not plan.refusal:
                items.append(
                    Proposal(
                        self.key,
                        "recruit_units",
                        {"unit": "spear", "count": plan.count, "reason": f"{why}: lanceiros"},
                        why,
                        "defesa básica contra cavalaria e saques",
                        cost=view.unit_cost("spear", plan.count),
                        factors=Factors(urgency=urgency, impact=0.45, risk_avoided=0.6),
                        horizon=Horizon.TACTICAL,
                        deadline=deadline,
                        confidence=0.85,
                    )
                )

        return items
