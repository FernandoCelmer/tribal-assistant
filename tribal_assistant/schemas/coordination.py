"""What the strategy page reads: each village's role, mode, next action, plan, reservations and deferrals."""

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RoleName = Literal["growth", "defense", "offensive", "support", "expansion"]


class CoordinationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    village_id: int
    village: str = ""
    created_at: datetime
    role: str
    mode: str
    goal: str
    next_review_at: datetime | None
    manual_role: bool = False
    data: dict[str, Any]

    @field_validator("data", mode="before")
    @classmethod
    def _parse(cls, value: Any) -> Any:
        return json.loads(value) if isinstance(value, str) else value


class RoleIn(BaseModel):
    role: RoleName | None = Field(default=None, description="Papel fixo da aldeia; vazio devolve a escolha ao coordenador.")
    reason: str = Field(default="", max_length=200)


class RoleOut(BaseModel):
    village_id: int
    role: str
    manual: bool
    reason: str


class ProposerOut(BaseModel):
    key: str
    title: str
    observes: str
    delivers: str
