"""Recruitment queue entry."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tribal_assistant.db.base import Base, TimestampMixin


class RecruitOrder(Base, TimestampMixin):
    __tablename__ = "recruit_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finishes_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    village: Mapped["Village"] = relationship(back_populates="recruit_orders")  # type: ignore[name-defined]  # noqa: F821
