"""Loads docs/ into the database and answers the agents' searches."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.docs.library import DocsLibrary
from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.core.repositories.documents import DocumentRepository
from tribal_assistant.core.schemas.docs import DocHit, DocOut, DocsSyncOut

DOCS_ROOT = Path("docs")


class DocsService:
    def __init__(self, session: AsyncSession, root: Path = DOCS_ROOT) -> None:
        self.session = session
        self.repo = DocumentRepository(session)
        self.library = DocsLibrary(root)

    async def sync(self) -> DocsSyncOut:
        files = self.library.files()
        if not files:
            return DocsSyncOut(files=0, updated=0, removed=0, chunks=0)

        known = await self.repo.checksums()
        seen, updated, chunks = set(), 0, 0
        for path in files:
            parts = self.library.chunks(path)
            relative = str(path.relative_to(self.library.root))
            seen.add(relative)
            chunks += len(parts)
            if parts and known.get(relative) != parts[0].checksum:
                await self.repo.replace(relative, parts)
                updated += 1

        removed = set(known) - seen
        await self.repo.remove(removed)
        await self.session.commit()
        return DocsSyncOut(files=len(files), updated=updated, removed=len(removed), chunks=chunks)

    async def search(self, query: str, limit: int = 5, category: str | None = None) -> list[DocHit]:
        hits = await self.repo.search(query, limit, category)
        return [DocHit(path=d.path, title=d.title, section=d.section, category=d.category, text=d.text, score=round(score, 4)) for d, score in hits]

    async def read(self, path: str) -> DocOut:
        rows = await self.repo.read(path)
        if not rows:
            raise NotFoundError(f"documento {path!r} não encontrado; use search_docs para achar o caminho")

        body = "\n\n".join(f"## {r.section}\n\n{r.text}" if r.section else r.text for r in rows)
        return DocOut(path=path, title=rows[0].title, category=rows[0].category, text=body)

    async def catalog(self) -> list[dict[str, str]]:
        return await self.repo.catalog()
