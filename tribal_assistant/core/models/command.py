"""Troop movement touching one of our villages."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tribal_assistant.core.db.base import Base, TimestampMixin
from tribal_assistant.core.db.scoping import AccountScoped


class Command(AccountScoped, Base, TimestampMixin):
    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    game_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    coords: Mapped[str | None] = mapped_column(String(16), nullable=True)
    arrival_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    village: Mapped["Village"] = relationship(back_populates="commands")  # type: ignore[name-defined]  # noqa: F821
