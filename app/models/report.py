"""Report ORM model — game report inbox."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, index=True, nullable=True)
    origin_coords: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    target_coords: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    loot_wood: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loot_clay: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loot_iron: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    haul_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
