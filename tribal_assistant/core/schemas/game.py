from datetime import datetime

from pydantic import BaseModel


class PlayerOut(BaseModel):
    name: str
    world: str
    points: int
    rank: int
    villages: int
    incomings: int
    premium_points: int
    new_reports: int
    new_mails: int
    new_quests: bool
    daily_bonus: bool
    protection_until: datetime | None
    synced_at: datetime | None


class BuildingOut(BaseModel):
    name: str
    label: str
    level: int
    max_level: int | None
    next_level: int | None
    next_wood: int | None
    next_clay: int | None
    next_iron: int | None
    next_pop: int | None
    build_time: int | None
    can_build: bool
    blocker: str | None
    queued_level: int | None
    queued_until: datetime | None


class UnitOut(BaseModel):
    name: str
    home: int
    total: int
    away: int
    available: bool
    max_recruit: int
    cost_wood: int | None
    cost_clay: int | None
    cost_iron: int | None
    cost_pop: int | None
    build_time: int | None
    blocker: str | None


class RecruitOrderOut(BaseModel):
    unit: str
    count: int
    finishes_at: datetime | None


class CommandOut(BaseModel):
    village_coords: str
    direction: str
    kind: str
    label: str
    coords: str | None
    arrival_at: datetime


class ScavengeOut(BaseModel):
    option_id: int
    name: str
    loot_factor: float
    is_locked: bool
    unlock_at: datetime | None
    return_at: datetime | None


class VillageOverview(BaseModel):
    id: int
    game_id: str | None
    name: str
    coords: str
    points: int
    wood: int
    clay: int
    iron: int
    storage: int
    pop_current: int
    pop_max: int
    wood_prod: int
    clay_prod: int
    iron_prod: int
    synced_at: datetime | None
    buildings: list[BuildingOut]
    units: list[UnitOut]
    recruit_orders: list[RecruitOrderOut]
    scavenge: list[ScavengeOut]


class ReportOut(BaseModel):
    game_id: str
    title: str
    category: str
    result: str | None
    is_new: bool
    received_at: datetime | None
    origin_coords: str | None
    target_coords: str | None
    loot_wood: int
    loot_clay: int
    loot_iron: int
    haul_total: int | None


class GameOverview(BaseModel):
    player: PlayerOut | None
    villages: list[VillageOverview]
    commands: list[CommandOut]
    reports: list[ReportOut]
