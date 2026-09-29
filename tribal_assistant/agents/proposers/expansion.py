"""Expansion: tracks the path to a nobleman and, in expansion role, reserves resources for it."""

from tribal_assistant.agents.coordination.budget import Reservation
from tribal_assistant.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.agents.coordination.strategy import Role
from tribal_assistant.agents.coordination.view import CoordinationView
from tribal_assistant.agents.proposers.base import Proposer

NOBLE_PATH = (("main", 20), ("smith", 20), ("market", 10), ("snob", 1))
NOBLE_COST = {"wood": 40000, "clay": 50000, "iron": 50000}


class ExpansionProposer(Proposer):
    key = "expansion"
    title = "Expansão"
    observes = "capacidade econômica, tropas e caminho da academia"
    delivers = "plano e reserva para conquistar outra aldeia"

    def progress(self, view: CoordinationView) -> float:
        levels = view.ctx.levels
        return sum(min(1.0, levels.get(b, 0) / lvl) for b, lvl in NOBLE_PATH) / len(NOBLE_PATH)

    async def reservations(self, view: CoordinationView) -> list[Reservation]:
        if view.role != Role.EXPANSION:
            return []

        free = {r: view.ctx.stock.get(r, 0) for r in ("wood", "clay", "iron")}
        share = {r: int(v * 0.3) for r, v in free.items()}
        return [Reservation("expansion", "strategic", "30% guardado para academia e nobre", share)]

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        progress = self.progress(view)
        view.note(Insight("noble_path", f"caminho do nobre: {progress:.0%}", Certainty.FACT, now(), 1.0, progress, self.key))

        if view.role != Role.EXPANSION or not view.free_slots:
            return []

        levels = view.ctx.levels
        for building, target in NOBLE_PATH:
            if levels.get(building, 0) < target and not view.guard.check_upgrade(view.ctx, building):
                return [
                    Proposal(
                        self.key,
                        "upgrade_building",
                        {"building": building, "reason": "caminho do nobre"},
                        f"{building} {target} é requisito da academia",
                        "aproxima a segunda aldeia",
                        cost=view.build_cost(building),
                        factors=Factors(urgency=0.1, impact=0.8, opportunity=0.3),
                        horizon=Horizon.STRATEGIC,
                        confidence=1.0,
                        purpose="expansion",
                        key=f"upgrade_building:{building}",
                    )
                ]

        return []
