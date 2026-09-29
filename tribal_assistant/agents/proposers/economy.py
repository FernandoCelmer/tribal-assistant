"""Economy: how much can be invested and when; storage, farm, reserves and market trades."""

from tribal_assistant.agents.coordination.budget import Reservation
from tribal_assistant.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.agents.coordination.view import CoordinationView
from tribal_assistant.agents.plan import PlanTracker
from tribal_assistant.agents.proposers.base import Proposer, clamp

MARKET_MINUTES = 360


class EconomyProposer(Proposer):
    key = "economy"
    title = "Economia"
    observes = "produção, recursos, armazém e custos"
    delivers = "armazém e fazenda à frente dos limites, reservas e trocas de excedente"

    async def reservations(self, view: CoordinationView) -> list[Reservation]:
        ctx = view.ctx
        storage = ctx.village.storage or 0
        items = []

        base = int(storage * view.config.resource_reserve)
        if base:
            items.append(
                Reservation(
                    "base",
                    "base",
                    "reserva mínima configurada",
                    {"wood": base, "clay": base, "iron": base},
                )
            )

        for building in PlanTracker.next_builds(ctx.plan)[:1]:
            cost = view.build_cost(building)
            if not cost or not view.free_slots:
                continue

            hours = view.estimator.hours_to_afford(cost)
            if hours <= 1.5:
                items.append(
                    Reservation(
                        f"plan:{building}",
                        "operation",
                        f"próxima obra do plano ({building}) em ~{hours:.1f}h",
                        {k: v for k, v in cost.items() if k != "pop"},
                    )
                )

        return items

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        estimator = view.estimator
        items = []

        storage_hours = estimator.storage_hours()
        horizon = max(3.0, estimator.queue_hours() + 2)
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
        if pop < 0.15 and self._buildable(view, "farm"):
            items.append(
                Proposal(
                    self.key,
                    "upgrade_building",
                    {"building": "farm", "reason": "população quase no limite"},
                    f"só {ctx.pop_free} de população livre",
                    "liberar obras e tropas",
                    cost=view.build_cost("farm"),
                    factors=Factors(urgency=clamp(1 - pop / 0.15), impact=0.7, risk_avoided=0.7),
                    horizon=Horizon.IMMEDIATE,
                    confidence=1.0,
                )
            )

        trade = await self._trade(view)
        if trade:
            items.append(trade)

        return items

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
        if max(stock.values()) - min(stock.values()) < 500 or not await view.cooldown(
            "market", 0.5
        ):
            return None

        offers = await view.actions.market_offers(ctx.game_id)
        choice = self.pick_offer(offers, stock, ctx.village.storage or 0)
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

    async def _own_offer(self, view: CoordinationView, stock: dict[str, int]) -> Proposal | None:
        plan = self.own_offer(stock, view.ctx.village.storage or 0)
        if plan is None or not await view.cooldown("market_offer", 2):
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
                "max_hours": 5,
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
    def own_offer(stock: dict[str, int], storage: int) -> tuple[str, str, int] | None:
        high = max(stock, key=stock.get)
        low = min(stock, key=stock.get)
        gap = stock[high] - stock[low]
        amount = min(1000, (gap // 2) // 100 * 100)
        if amount < 300 or stock[high] - amount < storage * 0.2:
            return None

        return high, low, amount

    @staticmethod
    def pick_offer(
        offers: list[dict], stock: dict[str, int], storage: int, max_minutes: int = MARKET_MINUTES
    ) -> dict | None:
        fits = [
            o
            for o in offers
            if o.get("can_accept")
            and o.get("receive")
            and o.get("pay")
            and o["receive"] != o["pay"]
            and o["pay_amount"] <= o["receive_amount"]
            and (o.get("minutes") or 0) <= max_minutes
            and stock[o["pay"]] - o["pay_amount"] >= storage * 0.2
            and stock[o["receive"]] + o["receive_amount"] <= storage
            and stock[o["pay"]] - o["pay_amount"] >= stock[o["receive"]]
        ]
        fits.sort(
            key=lambda o: (
                min(stock, key=stock.get) != o["receive"],
                -o["receive_amount"],
                o.get("minutes") or 0,
            )
        )
        return fits[0] if fits else None
