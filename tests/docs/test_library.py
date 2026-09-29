from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.docs.library import DocsLibrary
from tribal_assistant.core.services.docs import DocsService

ACADEMIA = """# Academia

Fonte: ajuda oficial

## Requisitos

Edifício principal 20, ferreiro 20 e mercado 10.

## Moedas

Cada nobre custa uma moeda de ouro: 28000 madeira, 30000 argila e 25000 ferro.
"""


def library(tmp_path: Path) -> Path:
    root = tmp_path / "docs"
    (root / "help").mkdir(parents=True)
    (root / "help" / "academia.md").write_text(ACADEMIA, encoding="utf-8")
    (root / "forum" / "tutoriais" / "raw").mkdir(parents=True)
    (root / "forum" / "tutoriais" / "coleta.md").write_text("# Coleta\n\nLanceiros coletam melhor.\n", encoding="utf-8")
    (root / "forum" / "tutoriais" / "raw" / "copia.md").write_text("# Copia\n\nignorar\n", encoding="utf-8")
    return root


def test_markdown_is_split_by_section_and_raw_folders_are_skipped(tmp_path: Path) -> None:
    lib = DocsLibrary(library(tmp_path))

    assert [str(p.relative_to(lib.root)) for p in lib.files()] == ["forum/tutoriais/coleta.md", "help/academia.md"]
    chunks = lib.chunks(lib.root / "help" / "academia.md")
    assert [c.section for c in chunks] == ["", "Requisitos", "Moedas"]
    assert chunks[0].title == "Academia" and chunks[0].category == "help"


async def test_sync_search_read_and_removal(session: AsyncSession, tmp_path: Path) -> None:
    root = library(tmp_path)
    service = DocsService(session, root)

    first = await service.sync()
    assert (first.files, first.updated) == (2, 2)
    assert (await service.sync()).updated == 0

    hits = await service.search("moeda de ouro academia")
    assert hits[0].path == "help/academia.md" and hits[0].section == "Moedas"

    doc = await service.read("help/academia.md")
    assert "## Requisitos" in doc.text and "28000 madeira" in doc.text

    (root / "forum" / "tutoriais" / "coleta.md").unlink()
    assert (await service.sync()).removed == 1
    assert await service.search("lanceiros") == []


async def test_docs_api(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/docs/search", params={"q": "academia"})).status_code == 200
    assert (await client.get("/api/v1/docs/read", params={"path": "nada/aqui.md"})).status_code == 404
