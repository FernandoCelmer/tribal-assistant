"""Village ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tribal_assistant.core.db.base import Base, TimestampMixin
from tribal_assistant.core.db.scoping import AccountScoped

if TYPE_CHECKING:
    from tribal_assistant.core.models.building import Building
    from tribal_assistant.core.models.command import Command
    from tribal_assistant.core.models.recruit_order import RecruitOrder
    from tribal_assistant.core.models.scavenge_option import ScavengeOption
    from tribal_assistant.core.models.unit import Unit


class Village(AccountScoped, Base, TimestampMixin):
    __tablename__ = "villages"
    __table_args__ = (UniqueConstraint("account_id", "game_id", name="uq_villages_account_game"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
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
