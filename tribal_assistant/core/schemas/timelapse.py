from datetime import datetime

from pydantic import BaseModel


class LevelChange(BaseModel):
    name: str
    label: str
    before: int
    after: int


class FrameOut(BaseModel):
    id: int
    taken_at: datetime
    width: int
    height: int
    points: int
    points_gained: int
    levels: dict[str, int]
    diff: list[LevelChange]
