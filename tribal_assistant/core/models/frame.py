"""Pictures of the village illustration taken during syncs, for the timelapse."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.core.db.base import Base
from tribal_assistant.core.db.scoping import AccountScoped


class VillageFrame(AccountScoped, Base):
    __tablename__ = "village_frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    taken_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    image: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    levels: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
