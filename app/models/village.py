"""Village ORM model."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.building import Building
    from app.models.unit import Unit


class Village(Base, TimestampMixin):
    __tablename__ = "villages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    coords: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    is_own: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    wood: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clay: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    iron: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pop_current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pop_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    buildings: Mapped[list["Building"]] = relationship(
        back_populates="village", cascade="all, delete-orphan"
    )
    units: Mapped[list["Unit"]] = relationship(
        back_populates="village", cascade="all, delete-orphan"
    )
