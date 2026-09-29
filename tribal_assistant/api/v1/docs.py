"""Docs endpoints: search the local library, read a document, reload docs/ into the database."""

from fastapi import APIRouter, Query

from tribal_assistant.api.deps import DocsServiceDep
from tribal_assistant.core.schemas.docs import DocHit, DocOut, DocsSyncOut

docs_router = APIRouter()


@docs_router.get("/search", response_model=list[DocHit])
async def search(
    service: DocsServiceDep,
    q: str = Query(min_length=2),
    limit: int = Query(default=5, ge=1, le=20),
    category: str | None = None,
) -> list[DocHit]:
    return await service.search(q, limit, category)


@docs_router.get("/read", response_model=DocOut)
async def read(service: DocsServiceDep, path: str = Query(min_length=3)) -> DocOut:
    return await service.read(path)


@docs_router.get("/catalog")
async def catalog(service: DocsServiceDep) -> list[dict[str, str]]:
    return await service.catalog()


@docs_router.post("/sync", response_model=DocsSyncOut)
async def sync(service: DocsServiceDep) -> DocsSyncOut:
    return await service.sync()
