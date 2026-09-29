"""Village state captured at every sync, for evolution charts."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.db.base import Base
from tribal_assistant.db.scoping import AccountScoped


class VillageSnapshot(AccountScoped, Base):
    __tablename__ = "village_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True, nullable=False)
    taken_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    wood: Mapped[int] = mapped_column(Integer, nullable=False)
    clay: Mapped[int] = mapped_column(Integer, nullable=False)
    iron: Mapped[int] = mapped_column(Integer, nullable=False)
    storage: Mapped[int] = mapped_column(Integer, nullable=False)
    pop_current: Mapped[int] = mapped_column(Integer, nullable=False)
    pop_max: Mapped[int] = mapped_column(Integer, nullable=False)
    wood_prod: Mapped[int] = mapped_column(Integer, nullable=False)
    clay_prod: Mapped[int] = mapped_column(Integer, nullable=False)
    iron_prod: Mapped[int] = mapped_column(Integer, nullable=False)
    troops_home: Mapped[int] = mapped_column(Integer, nullable=False)
    troops_total: Mapped[int] = mapped_column(Integer, nullable=False)
