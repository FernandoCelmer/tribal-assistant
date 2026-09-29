"""Farm target ORM model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.db.base import Base, TimestampMixin


class FarmTarget(Base, TimestampMixin):
    __tablename__ = "farm_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coords: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    template: Mapped[str] = mapped_column(String(8), default="A", nullable=False)
    last_attack_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_loot: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wall_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
