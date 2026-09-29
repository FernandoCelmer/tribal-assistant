"""Unit ORM model — troops per village."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tribal_assistant.db.base import Base, TimestampMixin


class Unit(Base, TimestampMixin):
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("village_id", "name", name="uq_units_village_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    home: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    away: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    support: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_recruit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_wood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_clay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_iron: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_pop: Mapped[int | None] = mapped_column(Integer, nullable=True)
    build_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocker: Mapped[str | None] = mapped_column(String(255), nullable=True)

    village: Mapped["Village"] = relationship(back_populates="units")  # type: ignore[name-defined]  # noqa: F821
