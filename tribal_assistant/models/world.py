"""Public world data: every village, player and tribe, plus world settings."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.db.base import Base
from tribal_assistant.db.scoping import WorldScoped


class WorldVillage(WorldScoped, Base):
    __tablename__ = "world_villages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    x: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    y: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    bonus_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class WorldPlayer(WorldScoped, Base):
    __tablename__ = "world_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ally_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    villages: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)


class WorldAlly(WorldScoped, Base):
    __tablename__ = "world_allies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    tag: Mapped[str] = mapped_column(String(32), nullable=False)
    members: Mapped[int] = mapped_column(Integer, nullable=False)
    villages: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    all_points: Mapped[int] = mapped_column(Integer, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)


class WorldSetting(WorldScoped, Base):
    __tablename__ = "world_settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
