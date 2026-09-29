from datetime import datetime

from pydantic import BaseModel


class WorldStatus(BaseModel):
    fetched_at: datetime | None
    villages: int
    players: int
    allies: int
    speed: float | None
    unit_speed: float | None


class NearbyVillage(BaseModel):
    id: int
    name: str
    coords: str
    points: int
    distance: float
    player_id: int
    player_name: str | None
    ally_tag: str | None
    is_barbarian: bool
    travel_minutes: dict[str, float]
