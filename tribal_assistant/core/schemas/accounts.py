"""Game accounts as the dashboard sees them; passwords are write-only."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    server: str
    world_url: str
    username: str
    headless: bool
    enabled: bool
    created_at: datetime


class AccountIn(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    world_url: str = Field(min_length=8, max_length=255, description="Ex.: https://br145.tribalwars.com.br")
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)
    headless: bool = False


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    password: str | None = Field(default=None, min_length=1, max_length=200)
    headless: bool | None = None
    enabled: bool | None = None
