from datetime import datetime

from pydantic import BaseModel, Field


class Affordability(BaseModel):
    label: str
    cost: dict[str, int]
    hours: float | None = Field(description="Hours until the stock pays the cost at the current production; 0 when it already does, null when never.")
    at: datetime | None


class VillageForecast(BaseModel):
    village_id: int
    name: str
    coords: str
    stock: dict[str, int]
    storage: int
    production: dict[str, int]
    hours_to_full: dict[str, float | None]
    storage_full_hours: float | None
    storage_full_at: datetime | None
    pop_free: int
    pop_max: int
    pop_ratio: float
    pop_lock_hours: float | None
    queue_hours: float
    incoming_attacks: int
    impact_hours: float | None
    next_build: Affordability | None
    afford: Affordability | None


class ScavengeRun(BaseModel):
    option_id: int
    loot_factor: float
    units: dict[str, int]
    carry: int
    haul: int
    base_minutes: float = Field(description="Run length before the world speed factor.")


class ScavengePlan(BaseModel):
    village_id: int
    free_options: list[int]
    units_home: dict[str, int]
    runs: list[ScavengeRun]
    note: str = ""
