"""Player ORM model — account-level snapshot."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Player(Base, TimestampMixin):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    world: Mapped[str] = mapped_column(String(32), nullable=False)
    ally_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    villages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incomings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    premium_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_mails: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_quests: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    daily_bonus: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    protection_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
