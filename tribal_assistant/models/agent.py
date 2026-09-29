"""What the village agents decided, why, and what the game answered."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.db.base import Base, TimestampMixin


class AgentDecision(Base, TimestampMixin):
    __tablename__ = "agent_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int | None] = mapped_column(ForeignKey("villages.id"), index=True, nullable=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    agent: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    arguments: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    result: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AgentGoal(Base, TimestampMixin):
    __tablename__ = "agent_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), unique=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)


class QuestState(Base, TimestampMixin):
    __tablename__ = "quests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quest_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    line_id: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    goals: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    can_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class QuestRewardState(Base, TimestampMixin):
    __tablename__ = "quest_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reward_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AgentSettingsRow(Base, TimestampMixin):
    __tablename__ = "agent_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    trigger: Mapped[str] = mapped_column(String(16), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    brain: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    villages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actions_ok: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actions_refused: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actions_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentStep(Base, TimestampMixin):
    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    village_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    agent: Mapped[str] = mapped_column(String(32), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    tool: Mapped[str | None] = mapped_column(String(48), nullable=True)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_error: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class VillagePlan(Base, TimestampMixin):
    __tablename__ = "village_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), unique=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    steps: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="rules", nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
