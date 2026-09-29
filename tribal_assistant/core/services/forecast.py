"""Forecasts and scavenging plans per village, from the synced state (no browser)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import ContextLoader, VillageContext
from tribal_assistant.core.agents.coordination.estimates import RESOURCES, Estimator
from tribal_assistant.core.agents.plan import PlanTracker
from tribal_assistant.core.agents.proposers.attack import SCAVENGERS, AttackProposer
from tribal_assistant.core.agents.proposers.economy import POP_WINDOW_HOURS, EconomyProposer
from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.core.repositories.game import GameRepository
from tribal_assistant.core.schemas.insight import (
    Affordability,
    ScavengePlan,
    ScavengeRun,
    VillageForecast,
)


def _finite(hours: float) -> float | None:
    return None if hours == float("inf") else round(hours, 2)


def _at(hours: float | None) -> datetime | None:
    return None if hours is None else datetime.now(UTC) + timedelta(hours=hours)


class ForecastService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def contexts(self, village_id: int | None) -> list[VillageContext]:
        contexts = await ContextLoader(self.session).load([village_id] if village_id else None)
        if village_id and not contexts:
            raise NotFoundError(f"aldeia {village_id} não sincronizada")

        return contexts

    async def villages(self, village_id: int | None = None, cost: dict[str, int] | None = None) -> list[VillageForecast]:
        return [await self.build(ctx, cost) for ctx in await self.contexts(village_id)]

    async def scavenge(self, village_id: int | None = None) -> list[ScavengePlan]:
        return [ScavengePlanner.plan(ctx) for ctx in await self.contexts(village_id)]

    async def build(self, ctx: VillageContext, cost: dict[str, int] | None = None) -> VillageForecast:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=POP_WINDOW_HOURS)
        samples = [(row.taken_at, row.pop_current) for row in await GameRepository(self.session).snapshots(ctx.id, since)]
        return self.of(ctx, cost, samples)

    @staticmethod
    def afford(estimator: Estimator, label: str, cost: dict[str, int]) -> Affordability:
        hours = _finite(estimator.hours_to_afford(cost))
        return Affordability(label=label, cost=cost, hours=hours, at=_at(hours))

    @classmethod
    def of(cls, ctx: VillageContext, cost: dict[str, int] | None = None, samples: list | None = None) -> VillageForecast:
        estimator = Estimator(ctx)
        village = ctx.village
        full = {r: _finite(h) for r, h in estimator.hours_to_full().items()}
        storage_hours = _finite(estimator.storage_hours())

        next_build = None
        for name in PlanTracker.next_builds(ctx.plan)[:1]:
            building = ctx.building(name)
            if building is not None:
                build_cost = {"wood": building.next_wood or 0, "clay": building.next_clay or 0, "iron": building.next_iron or 0}
                next_build = cls.afford(estimator, f"{name} {building.next_level or ''}".strip(), build_cost)

        impact = estimator.hours_to_impact()
        wanted = {r: int(cost.get(r, 0)) for r in RESOURCES} if cost and any(cost.values()) else None

        return VillageForecast(
            village_id=ctx.id,
            name=village.name,
            coords=village.coords,
            stock={r: int(ctx.stock.get(r, 0)) for r in RESOURCES},
            storage=village.storage or 0,
            production=estimator.production(),
            hours_to_full=full,
            storage_full_hours=storage_hours,
            storage_full_at=_at(storage_hours),
            pop_free=ctx.pop_free,
            pop_max=village.pop_max or 0,
            pop_ratio=round(estimator.pop_ratio(), 3),
            pop_lock_hours=_finite(EconomyProposer.pop_lock_hours(samples or [], ctx.pop_free)),
            queue_hours=round(estimator.queue_hours(), 2),
            incoming_attacks=len(estimator.incoming()),
            impact_hours=None if impact is None else round(impact, 2),
            next_build=next_build,
            afford=cls.afford(estimator, "custo pedido", wanted) if wanted else None,
        )


class ScavengePlanner:
    """Idle troops shared over the free scavenging tiers so every run ends together."""

    @staticmethod
    def plan(ctx: VillageContext, units: dict[str, int] | None = None) -> ScavengePlan:
        free = {o.option_id: o.loot_factor or 0.1 * o.option_id for o in ctx.village.scavenge if not o.is_locked and o.return_at is None}
        home = {}
        for name in SCAVENGERS:
            unit = ctx.unit(name)
            count = unit.home if unit else 0
            if units is not None:
                count = min(count, int(units.get(name, 0)))
            if count > 0:
                home[name] = count

        if not free:
            return ScavengePlan(village_id=ctx.id, free_options=[], units_home=home, runs=[], note="nenhum nível de coleta livre")

        parts = AttackProposer.split(home, free)
        runs = []
        for option, squad in sorted(parts.items()):
            carry = AttackProposer.carry(squad)
            haul = carry * free[option]
            runs.append(
                ScavengeRun(
                    option_id=option,
                    loot_factor=free[option],
                    units=squad,
                    carry=carry,
                    haul=int(haul),
                    base_minutes=round(AttackProposer.scavenge_seconds(haul) / 60, 1),
                )
            )

        note = "" if runs else "tropas em casa não chegam à população mínima por coleta"
        return ScavengePlan(village_id=ctx.id, free_options=sorted(free), units_home=home, runs=runs, note=note)
