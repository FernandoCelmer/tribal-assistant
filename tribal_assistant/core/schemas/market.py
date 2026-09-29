from pydantic import BaseModel, Field


class MarketOffer(BaseModel):
    receive: str | None
    receive_amount: int
    pay: str | None
    pay_amount: int
    player: str
    minutes: int | None
    can_accept: bool


class OwnOffer(BaseModel):
    id: str
    sell: str
    sell_amount: int
    buy: str
    buy_amount: int
    count: int
    max_hours: int | None
    parked: bool = Field(description="Asks more than it gives: a resource kept in the merchants, not a real trade.")


class Merchants(BaseModel):
    free: int
    total: int
    carry: int


class MarketOut(BaseModel):
    village_id: int
    merchants: Merchants
    offers: list[MarketOffer]
    own_offers: list[OwnOffer]


class KnightOut(BaseModel):
    village_id: int
    learnable: list[int]
    can_recruit: bool
    can_train: bool


class InventoryItem(BaseModel):
    key: str
    name: str | None
    detail: str
    usable: bool


class InventoryOut(BaseModel):
    village_id: int
    items: list[InventoryItem]
