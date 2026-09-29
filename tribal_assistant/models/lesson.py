"""What the assistant learned while playing: quests, game rules seen on screen and action outcomes."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.db.base import Base
from tribal_assistant.db.scoping import AccountScoped


class Lesson(AccountScoped, Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("account_id", "key", name="uq_lessons_account_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    data: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ok: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
