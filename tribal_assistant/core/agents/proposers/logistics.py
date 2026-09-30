"""Logistics: a village with room to spare feeds another own village stalled on resources, noble packages first."""

from sqlalchemy import select

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.estimates import Estimator
from tribal_assistant.core.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import tuning
from tribal_assistant.core.agents.knowledge import GameKnowledge
from tribal_assistant.core.agents.logistics import CARRY, Merchants, Need, ShipmentPlanner
from tribal_assistant.core.agents.plan import PlanTracker
from tribal_assistant.core.agents.proposers.base import Proposer
from tribal_assistant.core.agents.proposers.expansion import ExpansionProposer
from tribal_assistant.core.models.village import Village


class LogisticsProposer(Proposer):
    key = "logistics"
    title = "Logística"
    observes = "sobra e armazém de cada aldeia, obras e nobres travados nas outras aldeias da conta"
    delivers = "envio de recursos só entre aldeias próprias da mesma conta"

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        others = view.others
        if not others or ctx.levels.get("market", 0) < 1:
            return []

        knobs = tuning(view)
        storage = ctx.village.storage or 0
        pressed = max(ctx.stock.values(), default=0) >= storage * knobs.get("logistics.surplus_share") or view.estimator.storage_hours() <= knobs.get("logistics.full_hours")
        floor = ShipmentPlanner.floor(storage, knobs.get("logistics.keep_share"), view.guard.reserve(ctx))
        surplus = ShipmentPlanner.surplus(ctx.stock, storage, floor, self.own_need(view), pressed)
        if not any(surplus.values()):
            return []

        needs = []
        for other in others:
            if not await view.lessons.due(f"logistics:{other.id}", knobs.get("logistics.dest_hours")):
                continue

            need = await self.need(view, other)
            if need is not None:
                needs.append(need)

        capacity = Merchants.total(ctx.levels.get("market", 0)) * CARRY
        choice = ShipmentPlanner.choose(needs, surplus, capacity, knobs.int("logistics.min_lot"))
        if choice is None:
            return []

        need, lot = choice
        noble = need.priority == ShipmentPlanner.NOBLE
        view.note(Insight("logistics", f"envio para {need.name}: {need.reason}", Certainty.ESTIMATE, now(), 0.8, lot, self.key))
        return [
            Proposal(
                self.key,
                "send_resources",
                {"to_village_id": need.village_id, **lot, "reason": "nobre da conta" if noble else "aldeia própria travada"},
                need.reason,
                f"{sum(lot.values())} recursos para {need.name} ({need.coords})",
                cost=lot,
                factors=Factors(urgency=0.6 if noble else 0.4, impact=0.8 if noble else 0.5, opportunity=0.5, opportunity_cost=0.2),
                horizon=Horizon.TACTICAL,
                confidence=0.85,
                risks=["comerciantes ficam fora até voltar"],
            )
        ]

    @staticmethod
    def own_need(view: CoordinationView) -> dict[str, int]:
        for building in PlanTracker.next_builds(view.ctx.plan)[:1]:
            return {k: v for k, v in view.build_cost(building).items() if k != "pop"}

        return {}

    async def need(self, view: CoordinationView, other: VillageContext) -> Need | None:
        knobs = tuning(view)
        fill = knobs.get("logistics.dest_fill_share")
        storage = other.village.storage or 0
        room = ShipmentPlanner.room(other.stock, storage, fill)
        distance = ShipmentPlanner.distance(view.ctx.village.coords, other.village.coords)

        def build(priority: int, cost: dict[str, int], reason: str) -> Need | None:
            missing = ShipmentPlanner.missing(cost, other.stock, storage, fill)
            if not any(missing.values()):
                return None

            return Need(other.id, other.village.name, other.village.coords, missing, reason, priority, distance, room)

        if other.levels.get("snob", 0) >= 1:
            cost = await self.noble_cost(view, other)
            found = build(ShipmentPlanner.NOBLE, cost, f"{other.village.name} junta pacotes para o nobre")
            if found:
                return found

        cost, label = self.stalled_cost(other)
        if not cost or Estimator(other).hours_to_afford(cost) <= knobs.get("logistics.stall_hours"):
            return None

        return build(ShipmentPlanner.STALLED, cost, f"{other.village.name} travada por recurso em {label}")

    @staticmethod
    def stalled_cost(other: VillageContext) -> tuple[dict[str, int], str]:
        """Cost of the next plan build, or of the first missing prerequisite of a blocked one."""
        names = PlanTracker.next_builds(other.plan)[:1]
        if not names:
            blocked = [s.target for s in other.plan if s.kind == "build" and s.status == "blocked"]
            names = [next(iter(GameKnowledge.missing_requirements(blocked[0], other.levels)), "")] if blocked else []

        for name in names:
            building = other.building(name)
            if building is not None and building.next_level:
                return {"wood": building.next_wood or 0, "clay": building.next_clay or 0, "iron": building.next_iron or 0}, name

        return {}, ""

    @staticmethod
    async def noble_cost(view: CoordinationView, other: VillageContext) -> dict[str, int]:
        own = (await view.session.execute(select(Village.id).where(Village.is_own.is_(True)))).scalars().all()
        snob = other.unit("snob")
        world = await ExpansionProposer().world(view)
        return world.noble_cost(max(1, len(own)) + (snob.total if snob else 0))
