"""Building ORM model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Building(Base, TimestampMixin):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queued_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    village: Mapped["Village"] = relationship(back_populates="buildings")  # type: ignore[name-defined]  # noqa: F821
