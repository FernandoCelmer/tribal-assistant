"""Building ORM model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tribal_assistant.db.base import Base, TimestampMixin


class Building(Base, TimestampMixin):
    __tablename__ = "buildings"
    __table_args__ = (UniqueConstraint("village_id", "name", name="uq_buildings_village_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queued_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    max_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_wood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_clay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_iron: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_pop: Mapped[int | None] = mapped_column(Integer, nullable=True)
    build_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    can_build: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocker: Mapped[str | None] = mapped_column(String(255), nullable=True)

    village: Mapped["Village"] = relationship(back_populates="buildings")  # type: ignore[name-defined]  # noqa: F821
