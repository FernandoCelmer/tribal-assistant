from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VillageBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(max_length=120)
    coords: str = Field(pattern=r"^\d{1,3}\|\d{1,3}$")
    is_own: bool = True
    wood: int = 0
    clay: int = 0
    iron: int = 0
    storage: int = 0
    pop_current: int = 0
    pop_max: int = 0


class VillageCreate(VillageBase):
    game_id: str | None = None


class VillageUpdate(BaseModel):
    wood: int | None = None
    clay: int | None = None
    iron: int | None = None
    storage: int | None = None
    pop_current: int | None = None
    pop_max: int | None = None


class Village(VillageBase):
    id: int
    game_id: str | None
    created_at: datetime
    updated_at: datetime
