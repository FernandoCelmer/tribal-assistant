"""Local docs (official help, guides, forum tutorials) split in sections, searchable by the agents."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy import text as sql
from sqlalchemy.orm import Mapped, mapped_column

from tribal_assistant.core.db.base import Base

LANGUAGE = "portuguese"
VECTOR = f"(setweight(to_tsvector('{LANGUAGE}', search_title), 'A') || to_tsvector('{LANGUAGE}', search_text))"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("path", "chunk", name="uq_documents_path_chunk"),
        Index("ix_documents_search", sql(VECTOR), postgresql_using="gin").ddl_if(dialect="postgresql"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    chunk: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    search_title: Mapped[str] = mapped_column(Text, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(40), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
