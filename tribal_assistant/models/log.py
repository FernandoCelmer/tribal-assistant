"""Application log lines kept in the database for the dashboard."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.db.base import Base


class AppLog(Base):
    __tablename__ = "app_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    level: Mapped[str] = mapped_column(String(12), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    process: Mapped[str] = mapped_column(String(24), default="", nullable=False)
