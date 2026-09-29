"""Village ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.building import Building
    from app.models.command import Command
    from app.models.recruit_order import RecruitOrder
    from app.models.scavenge_option import ScavengeOption
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
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wood_prod: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clay_prod: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    iron_prod: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    buildings: Mapped[list["Building"]] = relationship(
        back_populates="village", cascade="all, delete-orphan"
    )
    units: Mapped[list["Unit"]] = relationship(
        back_populates="village", cascade="all, delete-orphan"
    )
    recruit_orders: Mapped[list["RecruitOrder"]] = relationship(
        back_populates="village", cascade="all, delete-orphan"
    )
    commands: Mapped[list["Command"]] = relationship(
        back_populates="village", cascade="all, delete-orphan"
    )
    scavenge_options: Mapped[list["ScavengeOption"]] = relationship(
        back_populates="village", cascade="all, delete-orphan"
    )
