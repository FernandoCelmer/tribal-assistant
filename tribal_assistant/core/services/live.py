"""Live reads that open the game in the browser: market, paladin and inventory. Only the server that plays can serve them."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.config import settings
from tribal_assistant.core.errors import ConflictError, NotFoundError
from tribal_assistant.core.game.actions import GameActions
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.schemas.market import (
    InventoryItem,
    InventoryOut,
    KnightOut,
    MarketOffer,
    MarketOut,
    Merchants,
    OwnOffer,
)


class LiveGameService:
    def __init__(self, session: AsyncSession, actions: GameActions | None = None) -> None:
        self.session = session
        self.actions = actions or GameActions()

    async def _village(self, village_id: int | None) -> Village:
        if not settings.play:
            raise ConflictError("Este servidor não joga (PLAY=false): use o servidor que está jogando")

        stmt = select(Village).where(Village.is_own.is_(True), Village.game_id.is_not(None))
        if village_id is not None:
            stmt = stmt.where(Village.id == village_id)

        village = (await self.session.execute(stmt.order_by(Village.id))).scalars().first()
        if village is None:
            raise NotFoundError(f"aldeia {village_id} não sincronizada" if village_id else "nenhuma aldeia própria sincronizada")

        return village

    async def market(self, village_id: int | None = None) -> MarketOut:
        village = await self._village(village_id)
        offers = await self.actions.market_offers(village.game_id)
        merchants = await self.actions.market_merchants(village.game_id)
        own = await self.actions.market.list_own_offers(village.game_id)
        return MarketOut(
            village_id=village.id,
            merchants=Merchants(**{k: int(merchants.get(k) or 0) for k in ("free", "total", "carry")}),
            offers=[MarketOffer(**{k: o.get(k) for k in MarketOffer.model_fields}) for o in offers],
            own_offers=[OwnOffer(**{k: o.get(k) for k in OwnOffer.model_fields if k != "parked"}, parked=o["buy_amount"] > o["sell_amount"]) for o in own],
        )

    async def knight(self, village_id: int | None = None) -> KnightOut:
        village = await self._village(village_id)
        state = await self.actions.knight_state(village.game_id)
        return KnightOut(village_id=village.id, learnable=list(state.get("learnable") or []), can_recruit=bool(state.get("can_recruit")), can_train=bool(state.get("can_train")))

    async def inventory(self, village_id: int | None = None) -> InventoryOut:
        village = await self._village(village_id)
        items = await self.actions.inventory(village.game_id)
        return InventoryOut(village_id=village.id, items=[InventoryItem(**{k: i.get(k) for k in InventoryItem.model_fields}) for i in items])
