"""What the tour through the game taught: each page compared with the last visit, turned into findings the agents act on."""

import hashlib
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.clock import Clock
from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.models.lesson import Lesson
from tribal_assistant.core.repositories.lessons import LessonRepository

NUMBER = re.compile(r"-?\d[\d.,]*")
RECRUITING = re.compile(r"recrut|aceitamos|procuramos|vagas abertas|aberta a novos|candidat|junte-se agora", re.I)
CLOSED = re.compile(r"não aceitamos|nao aceitamos|fechad[ao] para|sem vagas|apenas convidados", re.I)
POINTS = ("Pontos", "Pontuação", "Total de pontos")
MEMBERS = ("Número de membros", "Membros")
FINDINGS_KEPT = 40


def number(text: Any) -> int | None:
    match = NUMBER.search(re.sub(r"(?<=\d)\s*([.,])\s*(?=\d)", r"\1", str(text or "")))
    if not match:
        return None
    try:
        return int(match.group().replace(".", "").replace(",", ""))
    except ValueError:
        return None


def pick(pairs: dict[str, str], labels: tuple[str, ...]) -> int | None:
    for label in labels:
        if label in pairs:
            return number(pairs[label])
    return None


@dataclass
class Sighting:
    screen: str
    params: dict[str, str]
    label: str
    pairs: dict[str, str] = field(default_factory=dict)
    coords: list[str] = field(default_factory=list)
    text: str = ""

    @staticmethod
    def key_for(screen: str, params: dict[str, Any] | None) -> str:
        query = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
        return f"seen:{screen}" + (f":{query}" if query else "")

    @classmethod
    def of(cls, page: dict[str, Any]) -> "Sighting":
        return cls(
            screen=str(page.get("screen", "")),
            params={str(k): str(v) for k, v in dict(page.get("params") or {}).items()},
            label=str(page.get("label") or page.get("screen") or ""),
            pairs={str(k): str(v) for k, v in dict(page.get("pairs") or {}).items()},
            coords=[str(c) for c in page.get("coords") or []],
            text=str(page.get("text") or ""),
        )

    @property
    def key(self) -> str:
        return self.key_for(self.screen, self.params)

    def snapshot(self, at: datetime) -> dict[str, Any]:
        return {"at": at.isoformat(), "pairs": self.pairs, "coords": self.coords, "text": self.text[:600]}


@dataclass
class Finding:
    text: str
    subject: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class PageReader(ABC):
    """Reads one kind of page: what changed since the last visit and what that means."""

    screens: ClassVar[tuple[str, ...]] = ()

    def fits(self, sight: Sighting) -> bool:
        return sight.screen in self.screens

    @abstractmethod
    def read(self, sight: Sighting, before: dict[str, Any], hours: float, knobs: Knobs) -> list[Finding]:
        """Findings from this visit, given the previous snapshot of the same page (empty on a first visit)."""


class PlayerReader(PageReader):
    screens = ("info_player",)

    def fits(self, sight: Sighting) -> bool:
        return super().fits(sight) and bool(sight.params.get("id"))

    def read(self, sight: Sighting, before: dict[str, Any], hours: float, knobs: Knobs) -> list[Finding]:
        who, pid = sight.label.removeprefix("perfil de ").strip(), sight.params["id"]
        points, was = pick(sight.pairs, POINTS), pick(before.get("pairs") or {}, POINTS)
        subject = f"player:{pid}"
        if not before:
            return [Finding(f"{who}: primeira visita, {points or '?'} pontos e {len(sight.coords)} aldeia(s)", subject, {"name": who, "points": points})]

        found: list[Finding] = []
        gained = sorted(set(sight.coords) - set(before.get("coords") or []))
        lost = sorted(set(before.get("coords") or []) - set(sight.coords))
        if gained:
            found.append(Finding(f"{who} ganhou aldeia(s) {', '.join(gained[:5])} em {Clock.span(hours * 3600)}", subject, {"name": who, "expanding_at": datetime.now(UTC).isoformat(), "gained": gained}))
        if lost:
            found.append(Finding(f"{who} perdeu aldeia(s) {', '.join(lost[:5])}", subject, {"name": who, "lost": lost}))

        if points is not None and was is not None:
            if points == was and hours >= knobs.get("sightings.inactive_hours"):
                found.append(Finding(f"{who} parado em {points} pontos há {Clock.span(hours * 3600)}: provável inativo", subject, {"name": who, "inactive_since": before.get("at")}))
            elif points != was and hours > 0:
                rate = (points - was) / hours
                found.append(Finding(f"{who}: {was}→{points} pontos ({rate:+.0f}/h)", subject, {"name": who, "rate": round(rate, 1), "inactive_since": None}))
        return found


class AllyReader(PageReader):
    screens = ("info_ally",)

    def fits(self, sight: Sighting) -> bool:
        return super().fits(sight) and bool(sight.params.get("id"))

    def read(self, sight: Sighting, before: dict[str, Any], hours: float, knobs: Knobs) -> list[Finding]:
        tag, aid = sight.label, sight.params["id"]
        members, had = pick(sight.pairs, MEMBERS), pick(before.get("pairs") or {}, MEMBERS)
        signals = {"recruiting": bool(RECRUITING.search(sight.text)) and not CLOSED.search(sight.text), "closed": bool(CLOSED.search(sight.text)), "members": members}
        subject = f"ally:{aid}"

        found = []
        if not before or signals["recruiting"] != bool((before.get("signals") or {}).get("recruiting")):
            state = "recrutando" if signals["recruiting"] else "fechada" if signals["closed"] else "sem chamada de recrutamento"
            found.append(Finding(f"{tag}: {state}, {members or '?'} membros", subject, signals))
        elif members is not None and had is not None and members != had:
            found.append(Finding(f"{tag}: {had}→{members} membros", subject, signals))
        else:
            found.append(Finding("", subject, signals))
        return found


class ChangeReader(PageReader):
    """Any other page: which labelled numbers moved since the last visit; the map only shows a hover tooltip, so it is skipped."""

    NOISY: ClassVar[tuple[str, ...]] = ("map",)

    def fits(self, sight: Sighting) -> bool:
        return True

    def read(self, sight: Sighting, before: dict[str, Any], hours: float, knobs: Knobs) -> list[Finding]:
        if sight.screen in self.NOISY:
            return []

        old = before.get("pairs") or {}
        moved = [f"{k} {old[k]}→{v}" for k, v in sight.pairs.items() if k in old and old[k] != v][:4]
        return [Finding(f"{sight.label}: " + "; ".join(moved))] if moved else []


class SightingBook:
    READERS: ClassVar[tuple[PageReader, ...]] = (PlayerReader(), AllyReader(), ChangeReader())

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LessonRepository(session)

    @classmethod
    def findings(cls, sight: Sighting, before: dict[str, Any], hours: float, knobs: Knobs) -> list[Finding]:
        reader = next(r for r in cls.READERS if r.fits(sight))
        return reader.read(sight, before, hours, knobs)

    async def learn(self, pages: list[dict[str, Any]], knobs: Knobs) -> tuple[list[str], int]:
        """Findings of the tour and how many of its pages were read for the first time."""
        now = datetime.now(UTC)
        notes: list[str] = []
        first = 0

        for page in pages:
            sight = Sighting.of(page)
            row = await self.repo.get(sight.key)
            before = json.loads(row.data or "{}") if row else {}
            first += not before
            seen_at = Clock.aware(before.get("at"))
            hours = (now - seen_at).total_seconds() / 3600 if seen_at else 0.0

            found = self.findings(sight, before, hours, knobs)
            for finding in found:
                if finding.subject:
                    await self.repo.observe(finding.subject, finding.subject.split(":")[0], finding.data.get("name") or finding.subject, finding.text, finding.data, commit=False)
                if finding.text:
                    digest = hashlib.sha1(finding.text.encode()).hexdigest()[:12]
                    await self.repo.observe(f"sighting:{digest}", "sighting", finding.text[:255], finding.text, {"page": sight.key}, commit=False)
                    notes.append(finding.text)

            changed = any(f.text for f in found) and bool(before)
            signals = next((f.data for f in found if f.subject.startswith("ally:")), None)
            snapshot = sight.snapshot(now) | {"changed": changed} | ({"signals": signals} if signals else {})
            await self.repo.observe(sight.key, "seen", sight.label, "", snapshot, commit=False)

        await self.session.commit()
        return notes, first

    async def visits(self, keys: list[str]) -> dict[str, dict[str, Any]]:
        rows = (await self.session.execute(select(Lesson).where(Lesson.key.in_(keys)))).scalars().all()
        return {r.key: json.loads(r.data or "{}") for r in rows}

    async def expanding(self, hours: float) -> set[str]:
        """Player ids seen gaining villages within the last `hours`."""
        since = datetime.now(UTC) - timedelta(hours=hours)
        found = set()
        for row in await self.repo.list("player", limit=500):
            moment = Clock.aware(json.loads(row.data or "{}").get("expanding_at"))
            if moment and moment >= since:
                found.add(row.key.removeprefix("player:"))
        return found

    async def tribes(self) -> dict[str, dict[str, Any]]:
        return {row.key.removeprefix("ally:"): json.loads(row.data or "{}") for row in await self.repo.list("ally", limit=500)}

    async def summary(self, limit: int = 5) -> str:
        clock = Clock()
        rows = await self.repo.list("sighting", limit=FINDINGS_KEPT)
        rows = sorted(rows, key=lambda r: r.last_seen, reverse=True)[:limit]
        lines = [f"- {clock.relative(r.last_seen)}: {r.text}" for r in rows]
        return "Visto no passeio:\n" + "\n".join(lines) if lines else ""
