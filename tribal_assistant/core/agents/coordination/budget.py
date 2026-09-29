"""Resource and troop budget: reservations by purpose, so 'available' means free to spend."""

from dataclasses import dataclass, field
from typing import Any

from tribal_assistant.core.agents.context import VillageContext

RESOURCES = ("wood", "clay", "iron")


@dataclass
class Reservation:
    purpose: str
    kind: str
    reason: str
    cost: dict[str, int] = field(default_factory=dict)
    troops: dict[str, int] = field(default_factory=dict)
    applies_to: tuple[str, ...] = ()

    def covers(self, action: str) -> bool:
        return not self.applies_to or action in self.applies_to

    def to_dict(self) -> dict[str, Any]:
        return {"purpose": self.purpose, "kind": self.kind, "reason": self.reason, "cost": self.cost, "troops": self.troops}


class Budget:
    """Reads live stock from the context; reservations are held until their owner spends them."""

    KINDS = ("defense", "strategic", "operation", "base")

    def __init__(self, ctx: VillageContext) -> None:
        self.ctx = ctx
        self.reservations: list[Reservation] = []

    def reserve(self, reservation: Reservation) -> None:
        stock = self.stock()
        held = self.held()
        capped = {r: max(0, min(reservation.cost.get(r, 0), stock[r] - held[r])) for r in RESOURCES}
        reservation.cost = {r: v for r, v in capped.items() if v}
        self.reservations.append(reservation)

    def release(self, purpose: str) -> None:
        self.reservations = [r for r in self.reservations if r.purpose != purpose]

    def stock(self) -> dict[str, int]:
        return {r: max(0, self.ctx.stock.get(r, 0)) for r in RESOURCES}

    def held(self, excluding: str = "", action: str = "") -> dict[str, int]:
        total = dict.fromkeys(RESOURCES, 0)
        for reservation in self.reservations:
            if reservation.purpose == excluding or (action and not reservation.covers(action)):
                continue
            for r in RESOURCES:
                total[r] += reservation.cost.get(r, 0)

        return total

    def free(self, purpose: str = "", action: str = "") -> dict[str, int]:
        stock, held = self.stock(), self.held(excluding=purpose, action=action)
        return {r: max(0, stock[r] - held[r]) for r in RESOURCES}

    def affordable(self, cost: dict[str, int], purpose: str = "", action: str = "") -> bool:
        free = self.free(purpose, action)
        return all(cost.get(r, 0) <= free[r] for r in RESOURCES) and cost.get("pop", 0) <= self.ctx.pop_free

    def shortfall(self, cost: dict[str, int], purpose: str = "", action: str = "") -> dict[str, int]:
        free = self.free(purpose, action)
        return {r: cost.get(r, 0) - free[r] for r in RESOURCES if cost.get(r, 0) > free[r]}

    def committed_troops(self, excluding: str = "") -> dict[str, int]:
        total: dict[str, int] = {}
        for reservation in self.reservations:
            if reservation.purpose == excluding:
                continue
            for unit, count in reservation.troops.items():
                total[unit] = total.get(unit, 0) + count

        return total

    def free_troops(self, purpose: str = "") -> dict[str, int]:
        committed = self.committed_troops(excluding=purpose)
        return {u.name: max(0, u.home - committed.get(u.name, 0)) for u in self.ctx.village.units}

    def troops_available(self, troops: dict[str, int], purpose: str = "") -> bool:
        free = self.free_troops(purpose)
        return all(free.get(unit, 0) >= count for unit, count in troops.items())

    def to_dict(self) -> dict[str, Any]:
        return {
            "stock": self.stock(),
            "held": self.held(),
            "free": self.free(),
            "troops_committed": self.committed_troops(),
            "reservations": [r.to_dict() for r in self.reservations],
        }
