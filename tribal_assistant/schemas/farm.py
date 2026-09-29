from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FarmTargetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    coords: str = Field(pattern=r"^\d{1,3}\|\d{1,3}$")
    template: str = Field(default="A", pattern=r"^[ABC]$")
    wall_level: int = 0
    enabled: bool = True


class FarmTargetCreate(FarmTargetBase):
    pass


class FarmTarget(FarmTargetBase):
    id: int
    last_attack_at: datetime | None
    last_loot: int
    created_at: datetime
    updated_at: datetime


class FarmTickResult(BaseModel):
    dispatched: int
    skipped: int
    errors: list[str] = []
