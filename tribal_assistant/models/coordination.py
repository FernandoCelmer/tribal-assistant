"""Coordinator output per village and round, and the role each village plays."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.db.base import Base
from tribal_assistant.db.scoping import AccountScoped


class VillageStrategy(AccountScoped, Base):
    __tablename__ = "village_strategies"

    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CoordinationRound(AccountScoped, Base):
    __tablename__ = "coordination_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    goal: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    data: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
