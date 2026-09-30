"""Forecasts from the synced state: when storage fills, when population locks, when a cost is affordable."""

from datetime import UTC, datetime, timedelta
from typing import Any

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.core.agents.knobs import tuning

RESOURCES = ("wood", "clay", "iron")


class Estimator:
    def __init__(self, ctx: VillageContext) -> None:
        self.ctx = ctx
        self.village = ctx.village
        self.synced_at = self.village.synced_at.replace(tzinfo=None) if getattr(self.village, "synced_at", None) else now()

    def production(self) -> dict[str, int]:
        v = self.village
        return {"wood": v.wood_prod or 0, "clay": v.clay_prod or 0, "iron": v.iron_prod or 0}

    def hours_to_full(self) -> dict[str, float]:
        storage = self.village.storage or 0
        result = {}
        for resource, per_hour in self.production().items():
            room = storage - self.ctx.stock.get(resource, 0)
            result[resource] = 0.0 if room <= 0 else (room / per_hour if per_hour else float("inf"))

        return result

    def storage_hours(self) -> float:
        return min(self.hours_to_full().values())

    def pop_ratio(self) -> float:
        pop_max = self.village.pop_max or 1
        return self.ctx.pop_free / pop_max

    def hours_to_afford(self, cost: dict[str, int], free: dict[str, int] | None = None) -> float:
        free = free or {r: self.ctx.stock.get(r, 0) for r in RESOURCES}
        worst = 0.0
        for resource, per_hour in self.production().items():
            missing = cost.get(resource, 0) - free.get(resource, 0)
            if missing > 0:
                worst = max(worst, missing / per_hour if per_hour else float("inf"))

        return worst

    def queue_hours(self) -> float:
        ends = [q["until"] for q in self.ctx.queue if q.get("until")]
        if not ends:
            return 0.0

        latest = max(e.replace(tzinfo=None) if isinstance(e, datetime) else datetime.fromisoformat(str(e)).replace(tzinfo=None) for e in ends)
        return max(0.0, (latest - now()).total_seconds() / 3600)

    @staticmethod
    def moment(value: Any) -> datetime:
        at = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return at.astimezone(UTC).replace(tzinfo=None) if at.tzinfo else at

    def troops_back_hours(self) -> float | None:
        """Hours until the next troops come home: scavenging squads or our own commands."""
        backs = [s.return_at for s in getattr(self.village, "scavenge", None) or [] if getattr(s, "return_at", None)]
        backs += [c.get("arrival_at") for c in self.ctx.commands if c.get("direction") != "in" and c.get("arrival_at")]
        ahead = [hours for hours in ((self.moment(b) - now()).total_seconds() / 3600 for b in backs) if hours > 0]
        return min(ahead) if ahead else None

    def incoming(self) -> list[dict[str, Any]]:
        return [c for c in self.ctx.commands if c.get("direction") == "in" and c.get("kind") in ("attack", "noble")]

    def hours_to_impact(self) -> float | None:
        arrivals = []
        for command in self.incoming():
            arrival = command.get("arrival_at") or command.get("arrives_at")
            if arrival:
                at = datetime.fromisoformat(str(arrival).replace("Z", "+00:00")).replace(tzinfo=None)
                arrivals.append((at - now()).total_seconds() / 3600)

        if arrivals:
            return max(0.0, min(arrivals))

        return 0.0 if self.incoming() else None

    def deadline(self, hours: float) -> datetime | None:
        return None if hours == float("inf") else now() + timedelta(hours=hours)

    def insights(self) -> list[Insight]:
        ctx = self.ctx
        at = self.synced_at
        stock = ", ".join(f"{r} {ctx.stock.get(r, 0)}" for r in RESOURCES)
        full = self.hours_to_full()
        first = min(full, key=full.get)
        items = [
            Insight("stock", f"recursos: {stock} (armazém {self.village.storage})", Certainty.FACT, at, 1.0, dict(ctx.stock), "sync"),
            Insight("population", f"população livre: {ctx.pop_free} de {self.village.pop_max}", Certainty.FACT, at, 1.0, ctx.pop_free, "sync"),
            Insight("queue", f"fila de obras: {len(ctx.queue)} ordem(ns), termina em {self.queue_hours():.1f}h", Certainty.FACT, at, 1.0, len(ctx.queue), "sync"),
        ]

        if full[first] != float("inf"):
            items.append(
                Insight("storage_full", f"{first} enche o armazém em {full[first]:.1f}h", Certainty.ESTIMATE, now(), 0.85, full[first], "produção por hora")
            )

        if self.pop_ratio() < tuning(self.ctx).get("farm.pressure_ratio"):
            items.append(Insight("farm_pressure", "população quase no limite: fazenda vai travar obras e tropas", Certainty.ESTIMATE, now(), 0.9, self.pop_ratio(), "fazenda"))

        impact = self.hours_to_impact()
        if impact is not None:
            items.append(Insight("incoming", f"{len(self.incoming())} ataque(s) chegando, impacto em {impact:.1f}h", Certainty.FACT, at, 1.0, impact, "comandos"))

        return items
