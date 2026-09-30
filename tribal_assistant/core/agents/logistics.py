"""Resources moving between villages of the same account: merchants, surplus, needs and the shipment that fits."""

import math
from dataclasses import dataclass, field

RESOURCES = ("wood", "clay", "iron")
CARRY = 1000
MERCHANTS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 19, 26, 35, 46, 59, 74, 91, 110, 131, 154, 179, 206, 235)


class Merchants:
    @staticmethod
    def total(market_level: int) -> int:
        level = max(0, min(market_level, len(MERCHANTS) - 1))
        return MERCHANTS[level]

    @staticmethod
    def needed(amounts: dict[str, int], carry: int = CARRY) -> int:
        return math.ceil(sum(max(0, v) for v in amounts.values()) / max(1, carry))


@dataclass(frozen=True)
class Need:
    village_id: int
    name: str
    coords: str
    missing: dict[str, int]
    reason: str
    priority: int
    distance: float
    room: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.missing.values())


class ShipmentPlanner:
    """Pure rules: what a donor can spare, what a stalled village misses and the lot that moves between them."""

    NOBLE = 0
    STALLED = 1

    @staticmethod
    def distance(a: str, b: str) -> float:
        (ax, ay), (bx, by) = ((int(n) for n in c.split("|")) for c in (a, b))
        return round(math.hypot(ax - bx, ay - by), 1)

    @staticmethod
    def floor(storage: int, keep_share: float, reserve: int) -> int:
        return max(reserve, int(storage * keep_share))

    @classmethod
    def surplus(cls, stock: dict[str, int], storage: int, floor: int, own_need: dict[str, int], pressed: bool) -> dict[str, int]:
        """What the donor can spare above its floor and its own next use; nothing unless it is pressed for room."""
        if not pressed:
            return dict.fromkeys(RESOURCES, 0)

        return {r: max(0, stock.get(r, 0) - max(floor, own_need.get(r, 0))) for r in RESOURCES}

    @staticmethod
    def missing(cost: dict[str, int], stock: dict[str, int], storage: int, fill_share: float) -> dict[str, int]:
        """Resources short for a cost, never more than the receiver's storage can hold."""
        cap = int(storage * fill_share)
        return {r: max(0, min(cost.get(r, 0), cap) - stock.get(r, 0)) for r in RESOURCES}

    @staticmethod
    def room(stock: dict[str, int], storage: int, fill_share: float) -> dict[str, int]:
        cap = int(storage * fill_share)
        return {r: max(0, cap - stock.get(r, 0)) for r in RESOURCES}

    @staticmethod
    def fit(surplus: dict[str, int], need: Need, capacity: int) -> dict[str, int]:
        """The lot: what is short, what the donor spares and what fits the receiver, within the merchants' load."""
        lot = {r: max(0, min(surplus.get(r, 0), need.missing.get(r, 0), need.room.get(r, need.missing.get(r, 0)))) for r in RESOURCES}
        total = sum(lot.values())
        if total <= capacity or total <= 0:
            return lot

        scale = capacity / total
        return {r: int(v * scale) for r, v in lot.items()}

    @classmethod
    def choose(cls, needs: list[Need], surplus: dict[str, int], capacity: int, min_lot: int) -> tuple[Need, dict[str, int]] | None:
        """Noble packages first, then the closest stalled village; the first lot worth a trip."""
        for need in sorted(needs, key=lambda n: (n.priority, n.distance, -n.total)):
            lot = cls.fit(surplus, need, capacity)
            sent = sum(lot.values())
            if sent > 0 and sent >= min(min_lot, need.total):
                return need, lot

        return None
