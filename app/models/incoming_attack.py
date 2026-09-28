"""Incoming attack ORM model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class IncomingAttack(Base, TimestampMixin):
    __tablename__ = "incoming_attacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    origin_coords: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    target_coords: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    arrival_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_noble_guess: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
