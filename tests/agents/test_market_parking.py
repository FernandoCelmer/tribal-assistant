from types import SimpleNamespace

from tests.agents.builders import building, context, scavenge, unit
from tribal_assistant.core.agents.proposers.economy import EconomyProposer, IronParking
from tribal_assistant.core.agents.tools.act import CancelMarketOffer, ParkMarketOffer
from tribal_assistant.core.agents.tools.insight import PlanScavenge
from tribal_assistant.core.game.actions import ActionResult
from tribal_assistant.core.schemas.plan import PlanStep
from tribal_assistant.core.services.forecast import ForecastService, ScavengePlanner


def _offer(offer_id: str, sell_amount: int, buy_amount: int, *, sell: str = "iron", count: int = 1) -> dict:
    return {"id": offer_id, "sell": sell, "sell_amount": sell_amount, "buy": "wood", "buy_amount": buy_amount, "count": count}


def test_iron_parks_only_when_storage_is_pressed_or_an_attack_comes():
    assert IronParking.lots(4000, 5000, 0, 10.0, None) is None
    assert IronParking.lots(4500, 5000, 0, 10.0, None) == (1000, 3)
    assert IronParking.lots(3000, 5000, 0, 1.5, None) == (1000, 1)
    assert IronParking.lots(4500, 5000, 3000, 10.0, None) == (1000, 1)
    assert IronParking.lots(2600, 5000, 0, 10.0, 2.0) == (1000, 1)
    assert IronParking.lots(1700, 5000, 0, 10.0, 2.0) == (700, 1)
    assert IronParking.lots(1200, 5000, 0, 10.0, 2.0) is None


def test_parking_never_leaves_iron_below_the_tool_floor():
    storage = 4567
    amount, lots = IronParking.lots(4500, storage, 0, 1.0, 1.0)

    assert 4500 - amount * lots >= storage * ParkMarketOffer.FLOOR


def test_release_cancels_parked_iron_only_until_the_need_is_covered():
    offers = [_offer("1", 1000, 1100), _offer("2", 1000, 1000), _offer("3", 1000, 1100, count=2), _offer("4", 500, 600, sell="stone")]

    assert [o["id"] for o in IronParking.parked(offers)] == ["1", "3"]
    assert [o["id"] for o in IronParking.release(offers, 800, 2500)] == ["3"]
    assert [o["id"] for o in IronParking.release(offers, 0, 2500)] == ["3", "1"]
    assert IronParking.release(offers, 3000, 2500) == []


def test_iron_need_follows_plan_recruits_and_light_research():
    ctx = context(buildings=[building("main", 3), building("smith", 1), building("stable", 1), building("market", 1, cost=700)])
    ctx.village.units = [unit("axe", 0, cost=(60, 30, 40, 1)), unit("light", 0, available=False)]
    ctx.plan = [PlanStep(kind="build", target="market", amount=2), PlanStep(kind="recruit", target="axe", amount=10)]

    assert EconomyProposer.iron_need(ctx) == 2000

    ctx.village.units = [unit("axe", 0, cost=(60, 30, 40, 1)), unit("light", 0)]
    assert EconomyProposer.iron_need(ctx) == 700


class FakeMarket:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def cancel_offer(self, village_id: str, offer_id: str) -> ActionResult:
        self.calls.append(("cancel", offer_id))
        return ActionResult(True, "cancel_market_offer", "cancelada", {"offer": _offer(offer_id, 1000, 1100)})

    async def park(self, village_id: str, sell: str, amount: int, buy: str, lots: int, max_hours: int = 1) -> ActionResult:
        self.calls.append(("park", sell, amount, buy, lots, max_hours))
        return ActionResult(True, "park_market_offer", "estacionado")


def _box(ctx, *, dry_run: bool = False):
    return SimpleNamespace(ctx=ctx, dry_run=dry_run, actions=SimpleNamespace(market=FakeMarket()))


async def test_cancel_tool_returns_the_iron_to_the_stock():
    box = _box(context(stock=1000))

    outcome = await CancelMarketOffer().run(box, {"offer_id": "165611", "reason": "pesquisa"})

    assert outcome.ok
    assert box.actions.market.calls == [("cancel", "165611")]
    assert box.ctx.stock["iron"] == 2000
    assert not (await CancelMarketOffer().run(box, {"offer_id": "x1", "reason": "r"})).ok


async def test_park_tool_keeps_a_floor_and_spends_the_stock():
    box = _box(context(stock=4500, storage=5000))

    refused = await ParkMarketOffer().run(box, {"sell": "iron", "buy": "wood", "amount": 1000, "lots": 4, "reason": "r"})
    assert refused.text.startswith("RECUSADO")

    outcome = await ParkMarketOffer().run(box, {"sell": "iron", "buy": "wood", "amount": 1000, "lots": 3, "reason": "r"})
    assert outcome.ok
    assert box.actions.market.calls == [("park", "iron", 1000, "wood", 3, 1)]
    assert box.ctx.stock["iron"] == 1500


def test_scavenge_plan_shares_home_troops_over_free_tiers():
    ctx = context(units=[unit("spear", 100), unit("axe", 0)], scavenge_options=[scavenge(1), scavenge(2), scavenge(3, busy=True), scavenge(4, locked=True)])

    plan = ScavengePlanner.plan(ctx)

    assert plan.free_options == [1, 2]
    assert plan.units_home == {"spear": 100}
    assert sum(run.units.get("spear", 0) for run in plan.runs) == 100
    assert all(run.base_minutes > 30 for run in plan.runs)
    assert ScavengePlanner.plan(ctx, {"spear": 5}).note


async def test_plan_scavenge_tool_answers_json():
    ctx = context(units=[unit("spear", 40)], scavenge_options=[scavenge(1)])

    outcome = await PlanScavenge().run(SimpleNamespace(ctx=ctx), {})

    assert outcome.ok
    assert outcome.data["runs"][0]["units"] == {"spear": 40}


def test_forecast_reports_storage_population_and_affordability():
    ctx = context(stock=1000, storage=2000, pop_free=50)
    ctx.village.wood_prod = ctx.village.clay_prod = ctx.village.iron_prod = 500
    ctx.plan = [PlanStep(kind="build", target="main", amount=4)]

    forecast = ForecastService.of(ctx, {"wood": 2000, "clay": 0, "iron": 0})

    assert forecast.hours_to_full == {"wood": 2.0, "clay": 2.0, "iron": 2.0}
    assert forecast.storage_full_hours == 2.0
    assert forecast.pop_lock_hours is None
    assert forecast.next_build.hours == 0.0
    assert forecast.afford.hours == 2.0
    assert forecast.impact_hours is None
