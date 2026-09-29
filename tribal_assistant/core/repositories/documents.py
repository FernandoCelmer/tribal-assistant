"""Data access for the searchable docs."""

import re
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, delete, func, literal_column, or_, select
from sqlalchemy.dialects.postgresql import to_tsquery
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.docs.library import Chunk
from tribal_assistant.core.models.document import LANGUAGE, VECTOR, Document

ALL_WORDS_BONUS = 0.3
SYNONYMS = {
    "requisito": ("requerimento", "requer"),
    "requisitos": ("requerimentos", "requer"),
    "custo": ("custa", "preco", "requerimentos"),
    "custa": ("custo", "preco"),
    "producao": ("produz", "produzir"),
    "produz": ("producao",),
    "tropas": ("unidades",),
    "unidades": ("tropas",),
    "nobre": ("nobres", "noble"),
    "coleta": ("coletar", "coletando"),
}


def plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @property
    def postgres(self) -> bool:
        return self.session.get_bind().dialect.name == "postgresql"

    async def checksums(self) -> dict[str, str]:
        rows = await self.session.execute(select(Document.path, Document.checksum).distinct())
        return dict(rows.all())

    async def replace(self, path: str, chunks: list[Chunk]) -> None:
        await self.session.execute(delete(Document).where(Document.path == path))
        now = datetime.now(UTC).replace(tzinfo=None)
        self.session.add_all(
            Document(
                path=c.path,
                chunk=c.chunk,
                category=c.category,
                title=c.title,
                section=c.section,
                text=c.text,
                search_title=plain(f"{c.title} {c.section}"),
                search_text=plain(c.text),
                checksum=c.checksum,
                synced_at=now,
            )
            for c in chunks
        )

    async def remove(self, paths: set[str]) -> None:
        if paths:
            await self.session.execute(delete(Document).where(Document.path.in_(paths)))

    async def search(self, query: str, limit: int = 5, category: str | None = None) -> list[tuple[Document, float]]:
        words = [w for w in re.findall(r"\w+", plain(query)) if len(w) > 1]
        if not words:
            return []

        stmt = select(Document)
        if category:
            stmt = stmt.where(Document.category.startswith(category))

        if self.postgres:
            return await self._ranked(stmt, words, limit)

        rows = (await self.session.execute(stmt.where(or_(*(Document.search_title.contains(w) | Document.search_text.contains(w) for w in words))))).scalars().all()
        scored = [(doc, float(sum(doc.search_title.count(w) * 5 + doc.search_text.count(w) for w in words))) for doc in rows]
        return sorted(scored, key=lambda item: -item[1])[:limit]

    async def _ranked(self, stmt: Any, words: list[str], limit: int) -> list[tuple[Document, float]]:
        """Any word matches; title words weigh most and matching every word adds a bonus."""
        vector = literal_column(VECTOR)
        language = literal_column(f"'{LANGUAGE}'")
        groups = [" | ".join((w, *SYNONYMS.get(w, ()))) for w in words]
        any_word = to_tsquery(language, " | ".join(groups))
        every_word = to_tsquery(language, " & ".join(f"({g})" for g in groups))
        score = func.ts_rank(vector, any_word, 1) + case((vector.op("@@")(every_word), func.ts_rank(vector, every_word, 1) + ALL_WORDS_BONUS), else_=0)
        rows = await self.session.execute(stmt.add_columns(score).where(vector.op("@@")(any_word)).order_by(score.desc()).limit(limit))
        return [(doc, float(value)) for doc, value in rows.all()]

    async def read(self, path: str) -> Sequence[Document]:
        rows = await self.session.execute(select(Document).where(Document.path == path).order_by(Document.chunk))
        return rows.scalars().all()

    async def catalog(self) -> list[dict[str, Any]]:
        rows = await self.session.execute(
            select(Document.category, Document.path, Document.title).where(Document.chunk == 0).order_by(Document.category, Document.path)
        )
        return [{"category": c, "path": p, "title": t} for c, p, t in rows.all()]
