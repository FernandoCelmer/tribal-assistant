"""Market balance rule shared by the economy proposer and the trade tools."""

from tribal_assistant.core.agents.knobs import Knobs

LOT = 100


class MarketRule:
    """A trade is fine while it moves stock towards balance: the paid resource never ends below the received one."""

    @staticmethod
    def refusal(stock: dict[str, int], pay: str, amount: int, receive: str, receive_amount: int, storage: int) -> str | None:
        if pay == receive:
            return "troca do mesmo recurso"

        if amount > receive_amount:
            return f"razão ruim ({amount} por {receive_amount})"

        left = stock[pay] - amount
        if stock[receive] + receive_amount > storage:
            return f"{receive} estouraria o armazém"

        if left < stock[receive]:
            return f"pagar {amount} deixaria {pay} abaixo de {receive}"

        return None

    @staticmethod
    def for_build(stock: dict[str, int], cost: dict[str, int], storage: int, max_lot: int) -> tuple[str, str, int] | None:
        """When a build waits on one resource and the others have more than it needs, swap that surplus for exactly what is missing."""
        short = {r: cost.get(r, 0) - stock[r] for r in stock if cost.get(r, 0) > stock[r]}
        if len(short) != 1:
            return None

        buy, missing = next(iter(short.items()))
        surplus = {r: stock[r] - cost.get(r, 0) for r in stock if r != buy and stock[r] > cost.get(r, 0)}
        if not surplus:
            return None

        sell = max(surplus, key=surplus.get)
        need = -(-missing // LOT) * LOT
        amount = min(need, surplus[sell] // LOT * LOT, max_lot)
        if amount < LOT or stock[buy] + amount > storage:
            return None

        return sell, buy, amount

    @staticmethod
    def lot(stock: dict[str, int], min_gap: int | None = None, max_lot: int | None = None) -> tuple[str, str, int] | None:
        min_gap = min_gap if min_gap is not None else Knobs().int("market.min_gap")
        max_lot = max_lot if max_lot is not None else Knobs().int("market.max_lot")
        high = max(stock, key=stock.get)
        low = min(stock, key=stock.get)
        gap = stock[high] - stock[low]
        if gap < min_gap:
            return None

        return high, low, min(max_lot, (gap // 2) // LOT * LOT)
