"""Searchable docs: search hits, a full document and the sync report."""

from pydantic import BaseModel


class DocHit(BaseModel):
    path: str
    title: str
    section: str
    category: str
    text: str
    score: float


class DocOut(BaseModel):
    path: str
    title: str
    category: str
    text: str


class DocsSyncOut(BaseModel):
    files: int
    updated: int
    removed: int
    chunks: int
