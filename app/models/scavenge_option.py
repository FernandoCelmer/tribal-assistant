"""Scavenging option state per village."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ScavengeOption(Base, TimestampMixin):
    __tablename__ = "scavenge_options"
    __table_args__ = (
        UniqueConstraint("village_id", "option_id", name="uq_scavenge_options_village_option"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    option_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    loot_factor: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    unlock_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    return_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    squad_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    village: Mapped["Village"] = relationship(back_populates="scavenge_options")  # type: ignore[name-defined]  # noqa: F821
