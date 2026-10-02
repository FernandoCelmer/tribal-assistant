"""Economy: how much can be invested and when; storage, farm, reserves and market trades."""

import math
from datetime import UTC, datetime, timedelta

from tribal_assistant.core.agents.coordination.budget import FILLER, Reservation
from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import Knobs, knob, knob_int, tuning
from tribal_assistant.core.agents.market import MarketRule
from tribal_assistant.core.agents.plan import PlanTracker
from tribal_assistant.core.agents.proposers.base import Proposer, clamp
from tribal_assistant.core.agents.social.ledger import SocialLedger
from tribal_assistant.core.repositories.game import GameRepository

SPENDING = ("recruit_units", "train_knight", "use_item", "research_unit")


class IronParking:
    """Surplus iron waits in market offers nobody takes: safe from loot and from overflow, cancelled when needed."""

    LOT = 1000
    STEP = 100

    @classmethod
    def lots(cls, iron: int, storage: int, need: int, hours_full: float, impact_hours: float | None, knobs: Knobs | None = None) -> tuple[int, int] | None:
        """Amount per offer and how many offers, or None when the iron should stay home."""
        knobs = knobs or Knobs()
        threatened = impact_hours is not None and impact_hours <= knobs.get("iron_parking.threat_hours")
        pressed = storage > 0 and (iron >= storage * knobs.get("iron_parking.full_share") or hours_full <= knobs.get("iron_parking.soon_hours"))
        if not (threatened or pressed):
            return None

        keep = max(need, math.ceil(storage * knobs.get("iron_parking.floor_share" if threatened else "iron_parking.keep_share")))
        surplus = iron - keep
        if surplus >= cls.LOT:
            return cls.LOT, surplus // cls.LOT

        if surplus >= knobs.int("iron_parking.min_lot"):
            return surplus // cls.STEP * cls.STEP, 1

        return None

    @staticmethod
    def parked(offers: list[dict]) -> list[dict]:
        return [o for o in offers if o.get("sell") == "iron" and o.get("buy_amount", 0) > o.get("sell_amount", 0)]

    @classmethod
    def release(cls, offers: list[dict], iron: int, need: int) -> list[dict]:
        """Parked offers to cancel, biggest first, until the iron in stock covers the next use."""
        missing = need - iron
        chosen = []
        for offer in sorted(cls.parked(offers), key=lambda o: -o["sell_amount"] * o.get("count", 1)):
            if missing <= 0:
                break

            chosen.append(offer)
            missing -= offer["sell_amount"] * offer.get("count", 1)

        return chosen


class EconomyProposer(Proposer):
    key = "economy"
    title = "Economia"
    observes = "produção, recursos, armazém e custos"
    delivers = "armazém e fazenda à frente dos limites, reservas e trocas de excedente"

    async def reservations(self, view: CoordinationView) -> list[Reservation]:
        ctx = view.ctx
        storage = ctx.village.storage or 0
        items = []

        base = self.base_reserve(storage, view.ctx.policy.resource_reserve, ctx.stock, knob(view, "base_stock_share"))
        if any(base.values()):
            items.append(
                Reservation(
                    "base",
                    "base",
                    f"reserva mínima (não vale para obras; no máximo {knob(view, 'base_stock_share'):.0%} do estoque)",
                    base,
                    applies_to=SPENDING,
                )
            )

        for building in PlanTracker.next_builds(ctx.plan)[: tuning(ctx).int("plan_reserve.lookahead")]:
            cost = view.build_cost(building)
            if not cost or not view.free_slots:
                continue

            hours = view.estimator.hours_to_afford(cost)
            idle = not ctx.queue
            if hours <= knob(view, "plan_reserve.idle_hours" if idle else "plan_reserve.busy_hours"):
                items.append(
                    Reservation(
                        f"plan:{building}",
                        "operation",
                        f"próxima obra do plano ({building}) em ~{hours:.1f}h",
                        {k: v for k, v in cost.items() if k != "pop"},
                        exempt=() if idle else ("recruit_units",),
                        yields=(FILLER,),
                    )
                )

        return items

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        estimator = view.estimator
        items = []

        storage_hours = estimator.storage_hours()
        horizon = max(knob(view, "storage.horizon_hours"), estimator.queue_hours() + knob(view, "storage.queue_margin_hours"))
        if storage_hours < horizon and self._buildable(view, "storage"):
            items.append(
                Proposal(
                    self.key,
                    "upgrade_building",
                    {"building": "storage", "reason": "armazém enche antes da fila acabar"},
                    f"o armazém enche em {storage_hours:.1f}h",
                    "evitar perder produção por falta de espaço",
                    cost=view.build_cost("storage"),
                    factors=Factors(
                        urgency=self.urgency_from_hours(storage_hours, horizon),
                        impact=0.6,
                        risk_avoided=0.8,
                    ),
                    horizon=Horizon.IMMEDIATE,
                    deadline=estimator.deadline(storage_hours),
                    confidence=0.85,
                    risks=["consome recursos de recrutamento"],
                )
            )

        pop = estimator.pop_ratio()
        farm = ctx.building("farm")
        farm_hours = ((farm.build_time or 0) / 3600 if farm else 0) + estimator.queue_hours()
        lock_hours = self.pop_lock_hours(await self._pop_samples(view), ctx.pop_free)
        lead = knob(view, "farm.lead_hours")
        free_share = knob(view, "farm.free_share")
        early = lock_hours <= farm_hours + lead
        if (pop < free_share or early) and self._buildable(view, "farm"):
            why = f"população trava em ~{lock_hours:.1f}h e a fazenda leva ~{farm_hours:.1f}h" if early else f"só {ctx.pop_free} de população livre"
            items.append(
                Proposal(
                    self.key,
                    "upgrade_building",
                    {"building": "farm", "reason": "fazenda antes de a população travar"},
                    why,
                    "recrutamento e obras sem parar",
                    cost=view.build_cost("farm"),
                    factors=Factors(urgency=max(clamp(1 - pop / free_share), self.urgency_from_hours(lock_hours, farm_hours + lead)), impact=0.7, risk_avoided=0.7),
                    horizon=Horizon.IMMEDIATE,
                    confidence=1.0,
                )
            )

        trade = await self._trade(view)
        if trade:
            items.append(trade)

        if trade is None or trade.arguments.get("pay", trade.arguments.get("sell")) != "iron":
            items += await self._parking(view)

        return items

    @staticmethod
    def iron_need(ctx) -> int:
        """Iron the next use asks for: a plan build, a plan recruit batch or the light cavalry research."""
        batch = tuning(ctx).int("recruit.batch")
        needs = []
        for name in PlanTracker.next_builds(ctx.plan)[: tuning(ctx).int("plan.iron_lookahead")]:
            building = ctx.building(name)
            needs.append((building.next_iron or 0) if building else 0)

        for step in PlanTracker.next_recruits(ctx.plan)[: tuning(ctx).int("plan.recruit_lookahead")]:
            unit = ctx.unit(step.target)
            if unit is not None and unit.available:
                needs.append((unit.cost_iron or 0) * min(batch, max(0, step.amount - unit.total)))

        light = ctx.unit("light")
        if ctx.levels.get("stable", 0) >= 1 and ctx.levels.get("smith", 0) >= 1 and light is not None and not light.available:
            needs.append(tuning(ctx).int("economy.light_research_iron"))

        return max(needs, default=0)

    async def _parking(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        if ctx.levels.get("market", 0) < 1 or view.dry_run:
            return []

        iron = ctx.stock.get("iron", 0)
        need = self.iron_need(ctx)
        impact = view.estimator.hours_to_impact()
        memory = f"market_parked:{ctx.game_id}"

        if need > iron and impact is None and not await view.lessons.due(memory, knob(view, "market.park_memory_hours")) and await view.cooldown("market_release"):
            offers = await view.actions.market.list_own_offers(ctx.game_id)
            return [self._cancel(offer, need) for offer in IronParking.release(offers, iron, need)]

        plan = IronParking.lots(iron, ctx.village.storage or 0, need, view.estimator.hours_to_full()["iron"], impact, tuning(view))
        if plan is None or not await view.cooldown("market_park"):
            return []

        merchants = await view.actions.market_merchants(ctx.game_id)
        amount, lots = plan
        lots = min(lots, merchants.get("free", 0))
        if lots <= 0:
            return []

        await view.lessons.mark(memory)
        buy = "wood" if ctx.stock.get("wood", 0) <= ctx.stock.get("clay", 0) else "stone"
        why = f"ataque chega em {impact:.1f}h: ferro em oferta não é saqueado" if impact is not None else f"ferro {iron} de {ctx.village.storage} sem uso próximo"
        return [
            Proposal(
                self.key,
                "park_market_offer",
                {"sell": "iron", "buy": buy, "amount": amount, "lots": lots, "max_hours": knob_int(view, "iron_parking.offer_hours"), "reason": "estacionar ferro sobrando"},
                why,
                f"{amount * lots} ferro guardado nos comerciantes",
                cost={"iron": amount * lots},
                factors=Factors(urgency=0.5 if impact is not None else 0.3, impact=0.4, risk_avoided=0.7 if impact is not None else 0.4, opportunity_cost=0.1),
                horizon=Horizon.IMMEDIATE if impact is not None else Horizon.TACTICAL,
                confidence=0.75,
                risks=["alguém pode aceitar a oferta: ainda assim troca a favor"],
                key=f"park_market_offer:{amount}x{lots}",
            )
        ]

    def _cancel(self, offer: dict, need: int) -> Proposal:
        return Proposal(
            self.key,
            "cancel_market_offer",
            {"offer_id": offer["id"], "reason": "ferro necessário"},
            f"próximo uso pede {need} de ferro",
            f"+{offer['sell_amount'] * offer.get('count', 1)} ferro de volta",
            factors=Factors(urgency=0.6, impact=0.5, opportunity=0.4),
            horizon=Horizon.IMMEDIATE,
            confidence=0.9,
            key=f"cancel_market_offer:{offer['id']}",
        )

    @staticmethod
    def base_reserve(storage: int, share: float, stock: dict[str, int], stock_share: float) -> dict[str, int]:
        """A floor that never swallows the whole stock: the smaller of the policy share of storage and a self-tuned share of what is there."""
        return {r: int(min(storage * share, stock.get(r, 0) * stock_share)) for r in ("wood", "clay", "iron")}

    @staticmethod
    def pop_lock_hours(samples: list[tuple[datetime, int]], pop_free: int) -> float:
        """Hours until the farm is full at the pace population grew over the samples; inf when it is not growing."""
        if len(samples) < 2:
            return float("inf")

        (first_at, first), (last_at, last) = samples[0], samples[-1]
        hours = (last_at - first_at).total_seconds() / 3600
        if hours < 0.5 or last <= first:
            return float("inf")

        return max(0.0, pop_free) / ((last - first) / hours)

    @staticmethod
    async def _pop_samples(view: CoordinationView) -> list[tuple[datetime, int]]:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=knob(view, "economy.pop_window_hours"))
        rows = await GameRepository(view.session).snapshots(view.ctx.id, since)
        return [(row.taken_at, row.pop_current) for row in rows]

    @staticmethod
    def _buildable(view: CoordinationView, building: str) -> bool:
        return not view.guard.check_upgrade(view.ctx, building) or "recurso" in (
            view.guard.check_upgrade(view.ctx, building) or ""
        )

    async def _trade(self, view: CoordinationView) -> Proposal | None:
        ctx = view.ctx
        if ctx.levels.get("market", 0) < 1 or view.dry_run:
            return None

        stock = {
            "wood": ctx.stock.get("wood", 0),
            "stone": ctx.stock.get("clay", 0),
            "iron": ctx.stock.get("iron", 0),
        }
        urgent = await self._plan_trade(view, stock)
        if urgent is not None:
            return urgent

        if max(stock.values()) - min(stock.values()) < knob_int(view, "market.min_gap") or not await view.cooldown("market"):
            return None

        offers = await view.actions.market_offers(ctx.game_id)
        siblings = await self.managed_players(view)
        offers = [o for o in offers if o.get("player", "").split(" [")[0] not in siblings]
        choice = self.pick_offer(offers, stock, ctx.village.storage or 0, knob_int(view, "market.max_minutes"))
        if choice is None:
            return await self._own_offer(view, stock)

        return Proposal(
            self.key,
            "accept_market_offer",
            {
                "receive": choice["receive"],
                "receive_amount": choice["receive_amount"],
                "pay": choice["pay"],
                "amount": choice["pay_amount"],
                "player": choice["player"],
                "reason": f"trocar excedente de {choice['pay']} por {choice['receive']}",
            },
            f"{choice['pay']} sobrando e {choice['receive']} em falta",
            f"+{choice['receive_amount']} {choice['receive']} em {choice.get('minutes')} min",
            cost={
                "wood"
                if choice["pay"] == "wood"
                else "clay"
                if choice["pay"] == "stone"
                else "iron": choice["pay_amount"]
            },
            factors=Factors(urgency=0.3, impact=0.5, opportunity=0.6, opportunity_cost=0.2),
            horizon=Horizon.TACTICAL,
            confidence=0.8,
            risks=["recurso só chega depois da viagem do comerciante"],
        )

    async def _plan_trade(self, view: CoordinationView, stock: dict[str, int]) -> Proposal | None:
        """The next planned build waits on one resource while the others pile up: trade the pile for the gap now."""
        builds = PlanTracker.next_builds(view.ctx.plan)
        if not builds:
            return None

        building = builds[0]
        cost = view.build_cost(building)
        need = {"wood": cost.get("wood", 0), "stone": cost.get("clay", 0), "iron": cost.get("iron", 0)}
        trade = MarketRule.for_build(stock, need, view.ctx.village.storage or 0, knob_int(view, "market.max_lot"))
        if trade is None:
            return None

        merchants = await view.actions.market_merchants(view.ctx.game_id)
        free, carry = merchants.get("free", 0), merchants.get("carry") or 1000
        if free <= 0:
            return None

        sell, buy, amount = trade
        amount = min(amount, free * carry)
        return Proposal(
            self.key,
            "create_market_offer",
            {"sell": sell, "buy": buy, "amount": amount, "max_hours": knob_int(view, "market.offer_hours"), "reason": f"falta {buy} para {building}"},
            f"{building} espera {amount} de {buy}; {sell} sobrando",
            f"+{amount} {buy} e {building} começa antes",
            cost={"wood" if sell == "wood" else "clay" if sell == "stone" else "iron": amount},
            factors=Factors(urgency=0.6, impact=0.6, opportunity=0.6, opportunity_cost=0.1),
            horizon=Horizon.IMMEDIATE,
            confidence=0.7,
            risks=["comerciante fica preso até alguém aceitar"],
        )

    @staticmethod
    async def managed_players(view: CoordinationView) -> set[str]:
        """Players of the other accounts this assistant runs in the same world: never trade with them."""
        return await SocialLedger(view.session).managed()

    async def _own_offer(self, view: CoordinationView, stock: dict[str, int]) -> Proposal | None:
        plan = self.own_offer(stock, view.ctx.village.storage or 0, tuning(view))
        if plan is None or not await view.cooldown("market_offer"):
            return None

        merchants = await view.actions.market_merchants(view.ctx.game_id)
        if merchants.get("free", 0) <= 0:
            return None

        sell, buy, amount = plan
        amount = min(amount, merchants.get("carry") or 1000)
        return Proposal(
            self.key,
            "create_market_offer",
            {
                "sell": sell,
                "buy": buy,
                "amount": amount,
                "max_hours": knob_int(view, "market.offer_hours"),
                "reason": f"ofertar {sell} sobrando por {buy}",
            },
            f"nenhuma oferta boa de {buy}; {sell} sobrando",
            f"+{amount} {buy} quando alguém aceitar",
            cost={"wood" if sell == "wood" else "clay" if sell == "stone" else "iron": amount},
            factors=Factors(urgency=0.2, impact=0.4, opportunity=0.5, opportunity_cost=0.2),
            horizon=Horizon.TACTICAL,
            confidence=0.6,
            risks=["comerciante fica preso até alguém aceitar"],
        )

    @staticmethod
    def own_offer(stock: dict[str, int], storage: int, knobs: Knobs | None = None) -> tuple[str, str, int] | None:
        plan = MarketRule.lot(stock, (knobs or Knobs()).int("market.min_gap"), (knobs or Knobs()).int("market.max_lot"))
        if plan is None:
            return None

        high, low, amount = plan
        if MarketRule.refusal(stock, high, amount, low, amount, storage):
            return None

        return plan

    @staticmethod
    def pick_offer(
        offers: list[dict], stock: dict[str, int], storage: int, max_minutes: int | None = None
    ) -> dict | None:
        max_minutes = max_minutes if max_minutes is not None else Knobs().int("market.max_minutes")
        fits = [
            o
            for o in offers
            if o.get("can_accept")
            and o.get("receive")
            and o.get("pay")
            and (o.get("minutes") or 0) <= max_minutes
            and not MarketRule.refusal(stock, o["pay"], o["pay_amount"], o["receive"], o["receive_amount"], storage)
        ]
        fits.sort(
            key=lambda o: (
                min(stock, key=stock.get) != o["receive"],
                -o["receive_amount"],
                o.get("minutes") or 0,
            )
        )
        return fits[0] if fits else None
