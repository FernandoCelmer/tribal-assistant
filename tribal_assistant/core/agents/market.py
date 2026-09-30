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
    def lot(stock: dict[str, int], min_gap: int | None = None, max_lot: int | None = None) -> tuple[str, str, int] | None:
        min_gap = min_gap if min_gap is not None else Knobs().int("market.min_gap")
        max_lot = max_lot if max_lot is not None else Knobs().int("market.max_lot")
        high = max(stock, key=stock.get)
        low = min(stock, key=stock.get)
        gap = stock[high] - stock[low]
        if gap < min_gap:
            return None

        return high, low, min(max_lot, (gap // 2) // LOT * LOT)
