"""Farm target ORM model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.db.base import Base, TimestampMixin
from tribal_assistant.db.scoping import AccountScoped


class FarmTarget(AccountScoped, Base, TimestampMixin):
    __tablename__ = "farm_targets"
    __table_args__ = (UniqueConstraint("account_id", "coords", name="uq_farm_targets_account_coords"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coords: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    template: Mapped[str] = mapped_column(String(8), default="A", nullable=False)
    last_attack_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_loot: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wall_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
