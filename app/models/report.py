"""Report ORM model — battle report snapshots."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    origin_coords: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    target_coords: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    loot_wood: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loot_clay: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loot_iron: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wall_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    defender_alive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
