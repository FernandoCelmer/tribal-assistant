"""Infrastructure: which building best removes the current bottleneck, with its justification."""

from tribal_assistant.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.agents.coordination.strategy import Role
from tribal_assistant.agents.coordination.view import CoordinationView
from tribal_assistant.agents.knowledge import GameKnowledge
from tribal_assistant.agents.plan import PlanTracker
from tribal_assistant.agents.proposers.base import Proposer

PITS = ("wood", "stone", "iron")
NON_ECONOMIC = ("wall", "market", "hide", "watchtower", "statue", "garage")
CAPACITY = ("storage", "farm")
SCAVENGE_UNLOCK = {2: (250, 300, 250), 3: (1000, 1200, 1000), 4: (10000, 12000, 10000)}
PIT_RESOURCE = {"wood": "wood", "stone": "clay", "iron": "iron"}


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
        for index, building in enumerate(plan[:4]):
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

        if ctx.levels.get("main", 0) < 20 and self._ok(view, "main"):
            items.append(self._build(view, "main", "edifício principal acelera todas as obras", impact=0.6, opportunity=0.2))

        pit = self.bottleneck(view, plan)
        if self._ok(view, pit):
            weight = 0.7 if view.role in (Role.GROWTH, Role.EXPANSION) else 0.45
            resource = PIT_RESOURCE[pit]
            items.append(self._build(view, pit, f"{resource} é o que mais trava as próximas obras", impact=weight, opportunity=0.3))

        for option_id in PlanTracker.next_unlocks(ctx.plan)[:1]:
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

        return items

    @staticmethod
    def bottleneck(view: CoordinationView, plan: list[str]) -> str:
        """The pit whose resource the next builds miss the most, measured in hours of production."""
        production = view.estimator.production()
        demand = dict.fromkeys(("wood", "clay", "iron"), 0)
        for building in [*plan[:4], "main", "storage", "farm"]:
            for resource, amount in view.build_cost(building).items():
                if resource in demand:
                    demand[resource] += amount

        def pressure(pit: str) -> float:
            resource = PIT_RESOURCE[pit]
            missing = max(0, demand[resource] - view.ctx.stock.get(resource, 0))
            return missing / max(production[resource], 1)

        return max(PITS, key=lambda pit: (pressure(pit), -view.ctx.levels.get(pit, 0)))

    @staticmethod
    def capacity_needed(view: CoordinationView, building: str) -> bool:
        """Storage only when it fills within a day; farm only when free population drops under 30%."""
        if building == "storage":
            return view.estimator.storage_hours() < 24

        return view.estimator.pop_ratio() < 0.3

    @staticmethod
    def _ok(view: CoordinationView, building: str) -> bool:
        refusal = view.guard.check_upgrade(view.ctx, building)
        return refusal is None or "recurso" in refusal or "população" in refusal

    @staticmethod
    def _quests(view: CoordinationView) -> list[tuple[str, int]]:
        found = []
        for quest in view.ctx.quests:
            for goal in quest.get("goals", []):
                mapped = GameKnowledge.goal_building(f"{goal.get('title', '')} {goal.get('text', '')}")
                if not mapped:
                    continue

                level = mapped[1] or int(goal.get("target") or 1)
                if view.ctx.levels.get(mapped[0], 0) < level:
                    found.append((mapped[0], level))

        return found

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
