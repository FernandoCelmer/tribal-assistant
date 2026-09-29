"""Reads the Markdown under docs/ and splits every file into sections the agents can search."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
SKIPPED = {"raw", "screenshots"}
MAX_CHARS = 1500


@dataclass(frozen=True)
class Chunk:
    path: str
    chunk: int
    category: str
    title: str
    section: str
    text: str
    checksum: str


class DocsLibrary:
    def __init__(self, root: Path) -> None:
        self.root = root

    def files(self) -> list[Path]:
        if not self.root.is_dir():
            return []

        return sorted(p for p in self.root.rglob("*.md") if not SKIPPED & set(p.relative_to(self.root).parts[:-1]))

    def category(self, path: Path) -> str:
        parts = path.relative_to(self.root).parts[:-1]
        return "/".join(parts[:2]) if parts else "geral"

    @staticmethod
    def checksum(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def chunks(self, path: Path) -> list[Chunk]:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        text = IMAGE.sub("", raw)
        relative = str(path.relative_to(self.root))
        title = next((m.group(2) for line in text.splitlines() if (m := HEADING.match(line)) and len(m.group(1)) == 1), path.stem.replace("-", " "))

        sections: list[tuple[str, list[str]]] = [("", [])]
        for line in text.splitlines():
            found = HEADING.match(line)
            if found and len(found.group(1)) > 1:
                sections.append((found.group(2).strip(), []))
            elif not (found and found.group(2) == title):
                sections[-1][1].append(line)

        pieces = []
        for section, lines in sections:
            body = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
            for part in self.split(body):
                pieces.append((section, part))

        digest = self.checksum(raw)
        category = self.category(path)
        return [Chunk(relative, i, category, title[:255], section[:255], part, digest) for i, (section, part) in enumerate(pieces)]

    @staticmethod
    def split(body: str) -> list[str]:
        if not body:
            return []

        parts, current = [], ""
        for paragraph in body.split("\n\n"):
            if current and len(current) + len(paragraph) > MAX_CHARS:
                parts.append(current)
                current = ""
            current = f"{current}\n\n{paragraph}" if current else paragraph
            while len(current) > MAX_CHARS * 2:
                parts.append(current[:MAX_CHARS])
                current = current[MAX_CHARS:]

        if current:
            parts.append(current)
        return parts
