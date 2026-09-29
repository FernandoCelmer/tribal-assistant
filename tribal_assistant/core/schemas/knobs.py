"""Self-tuning decision parameters, as the panel and the MCP read and change them."""

from datetime import datetime

from pydantic import BaseModel, Field


class KnobChangeOut(BaseModel):
    at: str
    from_value: float | None = Field(default=None, alias="from", serialization_alias="from")
    to: float
    why: str


class KnobOut(BaseModel):
    name: str
    description: str
    default: float
    value: float
    reason: str
    updated_at: datetime | None = None
    history: list[KnobChangeOut]
    self_tuning: bool
    share: bool
    integer: bool


class KnobIn(BaseModel):
    value: float = Field(gt=0, description="New value; a share is a fraction up to 1.")


class KnobTuneChange(BaseModel):
    name: str
    value: float
    reason: str


class KnobTuneOut(BaseModel):
    changes: list[KnobTuneChange]
