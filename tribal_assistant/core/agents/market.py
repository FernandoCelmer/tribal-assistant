"""Market balance rule shared by the economy proposer and the trade tools."""

LOT = 100
MIN_GAP = 2 * LOT
MAX_LOT = 1000


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
    def lot(stock: dict[str, int]) -> tuple[str, str, int] | None:
        high = max(stock, key=stock.get)
        low = min(stock, key=stock.get)
        gap = stock[high] - stock[low]
        if gap < MIN_GAP:
            return None

        return high, low, min(MAX_LOT, (gap // 2) // LOT * LOT)
