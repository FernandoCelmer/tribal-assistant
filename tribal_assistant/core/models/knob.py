"""Self-tuning decision parameters, one row per account and name, with the history of each adjustment."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.core.db.base import Base
from tribal_assistant.core.db.scoping import AccountScoped


class TuningKnob(AccountScoped, Base):
    __tablename__ = "tuning_knobs"
    __table_args__ = (UniqueConstraint("account_id", "name", name="uq_tuning_knobs_account_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    history: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
