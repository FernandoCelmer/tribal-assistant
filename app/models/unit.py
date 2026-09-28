"""Unit ORM model — troops per village."""

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Unit(Base, TimestampMixin):
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("village_id", "name", name="uq_units_village_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    home: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    away: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    support: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    village: Mapped["Village"] = relationship(back_populates="units")  # type: ignore[name-defined]  # noqa: F821
