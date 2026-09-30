"""Infrastructure: which building best removes the current bottleneck, with its justification."""

from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import knob, knob_int, tuning
from tribal_assistant.core.agents.pacing import BuildPacing
from tribal_assistant.core.agents.plan import PlanTracker
from tribal_assistant.core.agents.proposers.base import Proposer
from tribal_assistant.core.agents.protection import Protection
from tribal_assistant.core.agents.quests import QuestRules

NON_ECONOMIC = ("wall", "market", "hide", "watchtower", "statue", "garage")
CAPACITY = ("storage", "farm")
SCAVENGE_UNLOCK = {2: (250, 300, 250), 3: (1000, 1200, 1000), 4: (10000, 12000, 10000)}
PIT_RESOURCE = {"wood": "wood", "stone": "clay", "iron": "iron"}
FILLER_EXTRA = ("wall", "hide", "storage", "farm")
FILLER_DEFENSIVE = ("wall", "hide")


class InfrastructureProposer(Proposer):
    key = "infrastructure"
    title = "Infraestrutura"
    observes = "níveis dos edifícios, filas e gargalos"
    delivers = "próxima melhoria com justificativa"

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        if not view.free_slots:
            return []

        items: list[Proposal] = []
        plan = PlanTracker.next_builds(ctx.plan)

        quest_buildings = {b for b, _ in self._quests(view)}
        for index, building in enumerate(plan[: knob_int(view, "build.plan_lookahead")]):
            if not self._ok(view, building):
                continue

            impact = 0.75 - index * 0.08
            if view.role == Role.GROWTH and building in NON_ECONOMIC and building not in quest_buildings:
                impact = 0.3
            if building in CAPACITY and not self.capacity_needed(view, building) and building not in quest_buildings:
                impact = 0.2

            items.append(self._build(view, building, f"passo {index + 1} do plano", impact=impact, opportunity=0.3, purpose=f"plan:{building}"))

        for building, level in self._quests(view):
            if self._ok(view, building):
                items.append(self._build(view, building, f"missão pede {building} {level}", impact=0.55, opportunity=0.75))

        military = BuildPacing.military_due(ctx.levels, Protection.active(ctx), tuning(view))
        for building in military:
            if self._ok(view, building):
                items.append(self._build(view, building, "2 de quartel e estábulo a cada 3 de EP", impact=0.62, opportunity=0.3))

        if not military and ctx.levels.get("main", 0) < BuildPacing.main_cap(ctx.levels, tuning(view)) and self._ok(view, "main"):
            items.append(self._build(view, "main", "edifício principal acelera todas as obras", impact=0.6, opportunity=0.2))

        pit = self.bottleneck(view, plan)
        if self._ok(view, pit):
            weight = 0.7 if view.role in (Role.GROWTH, Role.EXPANSION) else 0.45
            resource = PIT_RESOURCE[pit]
            items.append(self._build(view, pit, f"{resource} é o que mais trava as próximas obras", impact=weight, opportunity=0.3))

        filler = self.filler(view, plan)
        if filler:
            items.append(self._build(view, filler, "fila vazia: obra que cabe no estoque enquanto o plano espera", impact=0.4, opportunity=0.8))

        for option_id in PlanTracker.next_unlocks(ctx.plan)[: knob_int(view, "build.unlock_lookahead")]:
            if not view.guard.check_unlock_scavenge(ctx, option_id):
                items.append(
                    Proposal(
                        self.key,
                        "unlock_scavenge",
                        {"option_id": option_id, "reason": "passo do plano: coleta"},
                        f"desbloquear coleta {option_id}",
                        "renda de coleta sem arriscar tropas",
                        cost=dict(zip(("wood", "clay", "iron"), SCAVENGE_UNLOCK.get(option_id, (0, 0, 0)), strict=True)),
                        factors=Factors(urgency=0.2, impact=0.5, opportunity=0.6),
                        horizon=Horizon.TACTICAL,
                        confidence=0.8,
                        risks=["custo confirmado na tela do jogo"],
                    )
                )

        return self.trim(view, items)

    @staticmethod
    def trim(view: CoordinationView, items: list[Proposal]) -> list[Proposal]:
        """Builds that fit the stock all compete; of those still saving up, only the strongest stay, so the ranking is not all construction."""
        stock = view.ctx.stock

        def fits(p: Proposal) -> bool:
            return all(stock.get(r, 0) >= v for r, v in p.cost.items() if r in ("wood", "clay", "iron"))

        waiting = sorted((p for p in items if not fits(p)), key=lambda p: p.factors.impact, reverse=True)
        kept = {id(p) for p in waiting[: knob_int(view, "build.unaffordable_kept")]}
        return [p for p in items if fits(p) or id(p) in kept]

    @classmethod
    def filler(cls, view: CoordinationView, plan: list[str]) -> str | None:
        """With the queue idle and the next planned build still far away, the cheapest pit that fits the stock now."""
        if view.ctx.queue or not plan:
            return None

        if view.estimator.hours_to_afford(view.build_cost(plan[0])) <= knob(view, "filler_wait_hours"):
            return None

        stock = view.ctx.stock
        sheltered = Protection.active(view.ctx) and not Protection.ending(view.ctx)
        extra = [b for b in FILLER_EXTRA if not (sheltered and b in FILLER_DEFENSIVE)]
        candidates = dict.fromkeys([*BuildPacing.pits(view.ctx.levels, tuning(view)), *plan[1 : knob_int(view, "build.plan_lookahead")], *extra])
        affordable = [
            pit
            for pit in candidates
            if (cost := view.build_cost(pit)) and all(stock.get(r, 0) >= cost.get(r, 0) for r in ("wood", "clay", "iron")) and cls._ok(view, pit)
        ]
        return min(affordable, key=lambda pit: sum(view.build_cost(pit).get(r, 0) for r in ("wood", "clay", "iron")), default=None)

    @staticmethod
    def bottleneck(view: CoordinationView, plan: list[str]) -> str:
        """The pit whose resource the next builds miss the most, measured in hours of production."""
        production = view.estimator.production()
        demand = dict.fromkeys(("wood", "clay", "iron"), 0)
        for building in dict.fromkeys([*plan[: knob_int(view, "build.plan_lookahead")], "main"]):
            for resource, amount in view.build_cost(building).items():
                if resource in demand:
                    demand[resource] += amount

        for step in PlanTracker.next_recruits(view.ctx.plan)[: knob_int(view, "plan.recruit_lookahead")]:
            unit = view.ctx.unit(step.target)
            if unit is not None:
                for resource, per in (("wood", unit.cost_wood), ("clay", unit.cost_clay), ("iron", unit.cost_iron)):
                    demand[resource] += (per or 0) * knob_int(view, "build.recruit_demand_units")

        def pressure(pit: str) -> float:
            resource = PIT_RESOURCE[pit]
            missing = max(0, demand[resource] - view.ctx.stock.get(resource, 0))
            return missing / max(production[resource], 1)

        allowed = BuildPacing.pits(view.ctx.levels, tuning(view)) or ["wood"]
        return max(allowed, key=lambda pit: (pressure(pit), -view.ctx.levels.get(pit, 0)))

    @staticmethod
    def capacity_needed(view: CoordinationView, building: str) -> bool:
        """Storage only when it fills within the tuned hours; farm only when free population drops under the tuned share."""
        if building == "storage":
            return view.estimator.storage_hours() < knob(view, "capacity.storage_hours")

        return view.estimator.pop_ratio() < knob(view, "capacity.farm_free_share")

    @staticmethod
    def _ok(view: CoordinationView, building: str) -> bool:
        refusal = view.guard.check_upgrade(view.ctx, building)
        return refusal is None or "recurso" in refusal or "população" in refusal

    @staticmethod
    def _quests(view: CoordinationView) -> list[tuple[str, int]]:
        return [(b, lvl) for b, lvl, _ in QuestRules.building_goals(view.ctx.quests, view.ctx.levels, tuning(view))]

    def _build(
        self, view: CoordinationView, building: str, reason: str, impact: float, opportunity: float, purpose: str = ""
    ) -> Proposal:
        cost = view.build_cost(building)
        hours = view.estimator.hours_to_afford(cost)
        return Proposal(
            self.key,
            "upgrade_building",
            {"building": building, "reason": reason[:60]},
            reason,
            f"{building} nível {view.ctx.levels.get(building, 0) + 1}",
            cost=cost,
            factors=Factors(urgency=self.urgency_from_hours(hours, 4) * 0.5, impact=impact, opportunity=opportunity, opportunity_cost=0.1),
            horizon=Horizon.TACTICAL,
            confidence=1.0,
            purpose=purpose,
            key=f"upgrade_building:{building}",
        )
