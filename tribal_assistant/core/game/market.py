"""Own market offers: read them, park a surplus behind an offer and take it back. Never touches the premium exchange."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup, Tag
from loguru import logger

from tribal_assistant.core.game.human import human_delay
from tribal_assistant.core.game.session import game_session

if TYPE_CHECKING:
    from tribal_assistant.core.game.actions import ActionResult, GameActions

RESOURCES = ("wood", "stone", "iron")
DEFAULT_RATIO = (0.9, 1.1)
LOAD = 1000
RATIO_RE = re.compile(r"ratio_(min|max)\s*=\s*([^;]+);")
TERM_RE = re.compile(r"[+-]?[\d.]+")


class OwnOfferParser:
    """HTML of the market's own-offer screens in, plain dicts out."""

    @staticmethod
    def _number(text: str) -> int:
        digits = re.sub(r"\D", "", text)
        return int(digits) if digits else 0

    @classmethod
    def _goods(cls, cell: Tag) -> tuple[str, int] | None:
        icon = cell.select_one(".icon.header")
        if icon is None:
            return None

        resource = next((c for c in icon.get("class", []) if c in RESOURCES), None)
        if resource is None:
            return None

        return resource, cls._number(cell.get_text())

    @classmethod
    def offers(cls, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        for row in soup.select("tr.offer_container[data-id]"):
            goods = [g for g in (cls._goods(td) for td in row.find_all("td")) if g]
            if len(goods) < 2:
                continue

            offer_id = str(row["data-id"])
            (sell, sell_amount), (buy, buy_amount) = goods[:2]
            hours = soup.select_one(f"#offerText_{offer_id}")
            items.append(
                {
                    "id": offer_id,
                    "sell": sell,
                    "sell_amount": sell_amount,
                    "buy": buy,
                    "buy_amount": buy_amount,
                    "count": int(row.get("data-count") or 1),
                    "max_hours": cls._number(hours.get_text()) if hours else None,
                    "village": row.get("data-village") or None,
                }
            )

        return items

    @staticmethod
    def ratio(html: str) -> tuple[float, float]:
        """Lowest and highest buy/sell ratio the world allows for own offers."""
        found = {name: sum(float(t) for t in TERM_RE.findall(expr.replace(" ", ""))) for name, expr in RATIO_RE.findall(html)}
        low, high = DEFAULT_RATIO
        return round(found.get("min", low), 4), round(found.get("max", high), 4)

    @classmethod
    def merchants(cls, html: str) -> dict[str, int]:
        soup = BeautifulSoup(html, "lxml")
        free = soup.select_one("#market_merchant_available_count")
        total = soup.select_one("#market_merchant_total_count")
        carry = re.search(r"carry\s*:\s*(\d+)", html)
        return {
            "free": cls._number(free.get_text()) if free else 0,
            "total": cls._number(total.get_text()) if total else 0,
            "carry": int(carry.group(1)) if carry else LOAD,
        }


class Market:
    """Own offers of one village, through the market's own-offer screen."""

    def __init__(self, actions: GameActions) -> None:
        self.actions = actions

    async def _screen(self, village_id: str, mode: str = "own_offer") -> tuple[Any, str]:
        page = await self.actions._in_game(village_id, "market", mode=mode)
        return page, await page.content()

    async def list_own_offers(self, village_id: str) -> list[dict[str, Any]]:
        async with game_session.lock:
            _, html = await self._screen(village_id)
            return OwnOfferParser.offers(html)

    async def cancel_offer(self, village_id: str, offer_id: str) -> ActionResult:
        from tribal_assistant.core.game.actions import ActionResult

        async with game_session.lock:
            page, html = await self._screen(village_id)
            offer = next((o for o in OwnOfferParser.offers(html) if o["id"] == str(offer_id)), None)
            if offer is None:
                return ActionResult(False, "cancel_market_offer", f"oferta {offer_id} não está no mercado desta aldeia")

            await page.locator(f'#own_offers_table input[name="id_{offer_id}"]').first.check()
            await human_delay(400, 900)
            await self.actions._click_and_settle(page, page.locator('input[name="delete"]').first)
            self.actions._capture(await page.content(), "market-cancel")

            messages = await self.actions.screen_messages(page)
            if messages["errors"]:
                return ActionResult(False, "cancel_market_offer", " | ".join(messages["errors"]))

            _, html = await self._screen(village_id)
            if any(o["id"] == str(offer_id) for o in OwnOfferParser.offers(html)):
                return ActionResult(False, "cancel_market_offer", "a oferta continua no mercado")

        amount = offer["sell_amount"] * offer["count"]
        logger.info("Oferta {} cancelada: {} {} devolvidos", offer_id, amount, offer["sell"])
        return ActionResult(
            True,
            "cancel_market_offer",
            f"oferta {offer_id} cancelada: {amount} {offer['sell']} de volta ao armazém",
            {"offer": offer, "notices": messages["notices"]},
        )

    async def park(self, village_id: str, sell: str, amount: int, buy: str, lots: int, max_hours: int = 1) -> ActionResult:
        """Own offers asking the highest ratio the world allows, so the resource waits in the merchants, safe from looting."""
        from tribal_assistant.core.game.actions import ActionResult

        async with game_session.lock:
            page, html = await self._screen(village_id)
            merchants = OwnOfferParser.merchants(html)
            needed = -(-amount // (merchants["carry"] or LOAD)) * lots
            if merchants["free"] < needed:
                return ActionResult(False, "park_market_offer", f"comerciantes livres {merchants['free']}, precisa de {needed}")

            form = page.locator("#own_offer_form")
            if not await form.count():
                return ActionResult(False, "park_market_offer", "formulário de oferta não encontrado")

            _, high = OwnOfferParser.ratio(html)
            wanted = int(amount * high + 1e-6)
            await form.locator("#res_sell_amount").fill(str(amount))
            await form.locator(f"#res_sell_{sell}").check()
            await form.locator("#res_buy_amount").fill(str(wanted))
            await form.locator(f"#res_buy_{buy}").check()
            await form.locator('input[name="multi"]').fill(str(lots))
            await form.locator('input[name="max_time"]').fill(str(max_hours))
            await human_delay(500, 1100)
            await self.actions._click_and_settle(page, form.locator("#submit_offer"))
            after = await page.content()
            self.actions._capture(after, "market-park")

            messages = await self.actions.screen_messages(page)
            if messages["errors"]:
                return ActionResult(False, "park_market_offer", " | ".join(messages["errors"]))

        parked = [o for o in OwnOfferParser.offers(after) if o["sell"] == sell and o["buy"] == buy and o["buy_amount"] == wanted]
        logger.info("Estacionadas {}x {} {} pedindo {} {}", lots, amount, sell, wanted, buy)
        return ActionResult(
            True,
            "park_market_offer",
            f"{lots}x {amount} {sell} estacionado(s) pedindo {wanted} {buy} (até {max_hours}h)",
            {"offers": [o["id"] for o in parked], "buy_amount": wanted, "notices": messages["notices"]},
        )
