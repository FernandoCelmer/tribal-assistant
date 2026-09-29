"""Challenges (game achievements) and how the agents pursue them."""

from datetime import datetime

from pydantic import BaseModel


class ChallengeOut(BaseModel):
    group: str
    name: str
    tier: str | None = None
    level: int
    description: str
    current: int | None = None
    target: int | None = None
    ratio: float | None = None
    earned: bool
    done: bool
    status: str
    agent: str
    how: str


class ChallengesOut(BaseModel):
    updated_at: datetime | None = None
    items: list[ChallengeOut]
    summary: dict[str, int]
