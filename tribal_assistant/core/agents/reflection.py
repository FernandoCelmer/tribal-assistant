"""Reflection: the bot looks back at how the last hours went, writes conclusions tied to a measure and lets the numbers confirm or drop them."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.clock import Clock
from tribal_assistant.core.agents.knob_rules import Metrics
from tribal_assistant.core.agents.knobs import Knobs, KnobStore
from tribal_assistant.core.agents.learning import LessonBook
from tribal_assistant.core.agents.sightings import SightingBook
from tribal_assistant.core.agents.writer import ModelWriter
from tribal_assistant.core.models.snapshot import VillageSnapshot
from tribal_assistant.core.repositories.lessons import LessonRepository

TOPIC = "belief"
DUE = "reflection"
EXPECT = {"cair": "down", "subir": "up", "down": "down", "up": "up"}
LIST = re.compile(r"\[.*\]", re.S)

MEASURES = {
    "points_per_hour": "pontos ganhos por hora (maior é melhor)",
    "builds_done": "níveis de edifício concluídos na janela (maior é melhor)",
    "idle_queue": "fração das rodadas com a fila de obras parada",
    "idle_recruiting": "fração das rodadas sem recrutamento em andamento",
    "army_stalled": "fração das rodadas sem recrutar nada",
    "recruit_starved": "fração das rodadas com recrutamento sem recurso",
    "stock_empty": "fração das rodadas com estoque quase zerado",
    "storage_full": "fração das rodadas com armazém cheio",
    "pop_locked": "fração das rodadas com população travada",
    "scavenge_idle": "fração das rodadas com coleta parada",
    "iron_short": "fração das rodadas com obras esperando ferro",
    "raids_lost": "fração das rodadas com saques perdendo tropas",
    "no_targets": "fração das rodadas sem bárbara no alcance",
    "farm_full": "fração dos saques voltando com carga cheia (maior é melhor)",
    "threatened": "fração das rodadas com ataques chegando",
    "repetition": "fração das rodadas repetindo as mesmas ações",
}

SYSTEM = (
    "Você é o estrategista de uma conta de Tribal Wars (servidor brasileiro) revendo as últimas horas de jogo. "
    "Leia as medidas, as conclusões atuais com a confiança de cada uma e os fatos, e escreva até 3 conclusões NOVAS "
    "e úteis: o que trava o crescimento, o que funciona, o que mudar. Cada conclusão precisa de uma medida da lista "
    "que deve melhorar se ela estiver certa e for seguida. Não repita conclusões existentes. Responda só com JSON: "
    '[{"conclusao": "frase curta", "acao": "o que fazer, em até 12 palavras", "medida": "nome da medida", "espera": "cair" ou "subir"}]'
)


@dataclass
class Belief:
    key: str
    statement: str
    action: str
    measure: str
    expect: str
    baseline: float
    confidence: float
    created_at: str
    checked_at: str
    confirmed: int = 0
    refuted: int = 0

    @classmethod
    def load(cls, key: str, data: dict[str, Any]) -> "Belief | None":
        try:
            return cls(key=key, **{f.name: data[f.name] for f in fields(cls) if f.name != "key"})
        except KeyError:
            return None

    def verdict(self, value: float, margin: float) -> int:
        delta = value - self.baseline
        if abs(delta) < margin * max(1.0, abs(self.baseline)):
            return 0
        return 1 if (delta > 0) == (self.expect == "up") else -1

    def decayed(self, now: datetime, half_life: float) -> float:
        checked = Clock.aware(self.checked_at) or now
        hours = max(0.0, (now - checked).total_seconds() / 3600)
        return self.confidence * 0.5 ** (hours / half_life)


class Reflection:
    def __init__(self, session: AsyncSession, writer: ModelWriter | None = None) -> None:
        self.session = session
        self.repo = LessonRepository(session)
        self.writer = writer or ModelWriter()

    async def measures(self, knobs: Knobs) -> dict[str, float]:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=knobs.get("reflection.window_hours"))
        metrics: Metrics = await KnobStore(self.session).metrics(since)
        values = {name: float(getattr(metrics, name)) for name in MEASURES if hasattr(metrics, name)}
        values["points_per_hour"] = await self.points_per_hour(since)
        return values

    async def points_per_hour(self, since: datetime) -> float:
        rows = (
            await self.session.execute(
                select(VillageSnapshot.village_id, func.min(VillageSnapshot.taken_at), func.max(VillageSnapshot.taken_at))
                .where(VillageSnapshot.taken_at >= since)
                .group_by(VillageSnapshot.village_id)
            )
        ).all()
        gained, hours = 0, 0.0
        for village_id, first, last in rows:
            if last <= first:
                continue
            points = dict(
                (
                    await self.session.execute(
                        select(VillageSnapshot.taken_at, VillageSnapshot.points).where(VillageSnapshot.village_id == village_id, VillageSnapshot.taken_at.in_([first, last]))
                    )
                ).all()
            )
            gained += points.get(last, 0) - points.get(first, 0)
            hours = max(hours, (last - first).total_seconds() / 3600)
        return round(gained / hours, 2) if hours else 0.0

    async def beliefs(self) -> list[Belief]:
        found = []
        for row in await self.repo.list(TOPIC, limit=200):
            data = json.loads(row.data or "{}")
            if data.get("dropped"):
                continue
            belief = Belief.load(row.key, data)
            if belief:
                found.append(belief)
        return found

    async def save(self, belief: Belief, dropped: bool = False) -> None:
        title = f"{belief.statement} ({belief.confidence:.0%})"
        await self.repo.observe(belief.key, TOPIC, title, belief.action, {**asdict(belief), "dropped": dropped}, commit=False)

    async def verify(self, beliefs: list[Belief], values: dict[str, float], knobs: Knobs) -> list[str]:
        now = datetime.now(UTC)
        settle = timedelta(hours=knobs.get("reflection.interval_hours"))
        notes = []
        for belief in beliefs:
            belief.confidence = belief.decayed(now, knobs.get("reflection.half_life_hours"))
            created = Clock.aware(belief.created_at) or now
            verdict = belief.verdict(values.get(belief.measure, belief.baseline), knobs.get("reflection.margin")) if now - created >= settle else 0

            if verdict > 0:
                belief.confirmed += 1
                belief.confidence = min(1.0, belief.confidence + knobs.get("reflection.step"))
                notes.append(f"confirmada: {belief.statement}")
            elif verdict < 0:
                belief.refuted += 1
                belief.confidence = max(0.0, belief.confidence - knobs.get("reflection.step") * 1.5)
                notes.append(f"contrariada: {belief.statement}")

            belief.checked_at = now.isoformat()
            dropped = belief.confidence < knobs.get("reflection.drop_below")
            if dropped:
                notes.append(f"descartada: {belief.statement}")
            await self.save(belief, dropped)
        return notes

    @staticmethod
    def parse(reply: str | None) -> list[dict[str, Any]]:
        match = LIST.search(reply or "")
        if not match:
            return []
        try:
            items = json.loads(match.group())
        except json.JSONDecodeError:
            return []
        return [i for i in items if isinstance(i, dict)]

    async def facts(self, values: dict[str, float], beliefs: list[Belief]) -> str:
        current = "\n".join(f"- {b.statement} → {b.action} [{b.measure} deve {'subir' if b.expect == 'up' else 'cair'}; confiança {b.confidence:.0%}]" for b in beliefs) or "- nenhuma"
        measures = "\n".join(f"- {name} = {values.get(name, 0):.2f}: {MEASURES[name]}" for name in MEASURES)
        lessons = await LessonBook(self.session).summary()
        sights = await SightingBook(self.session).summary(8)
        absences = await self.repo.get("absence:history")
        gaps = json.loads(absences.data or "{}").get("gaps", [])[-5:] if absences else []
        away = "\n".join(f"- {g.get('hours')}h parado a partir de {g.get('start')}" for g in gaps) or "- nenhuma"
        return f"Medidas das últimas horas:\n{measures}\n\nConclusões atuais:\n{current}\n\nAusências recentes:\n{away}\n\n{sights}\n\n{lessons}"

    async def reflect(self, values: dict[str, float], beliefs: list[Belief], knobs: Knobs) -> list[str]:
        room = knobs.int("reflection.max_beliefs") - len(beliefs)
        if room <= 0:
            return []

        reply = await self.writer.ask(SYSTEM, await self.facts(values, beliefs), "a reflexão")
        known = {b.statement.lower() for b in beliefs}
        now = datetime.now(UTC).isoformat()
        notes = []
        for item in self.parse(reply)[:room]:
            statement, measure = str(item.get("conclusao") or "").strip()[:200], str(item.get("medida") or "")
            expect = EXPECT.get(str(item.get("espera") or "").lower())
            if not statement or measure not in MEASURES or expect is None or statement.lower() in known:
                continue

            key = f"{TOPIC}:{hashlib.sha1(statement.lower().encode()).hexdigest()[:12]}"
            belief = Belief(key, statement, str(item.get("acao") or "")[:120], measure, expect, values.get(measure, 0.0), knobs.get("reflection.initial_confidence"), now, now)
            await self.save(belief)
            known.add(statement.lower())
            notes.append(f"nova: {statement}")
        return notes

    async def run(self, force: bool = False) -> list[str]:
        knobs = await KnobStore(self.session).load()
        book = LessonBook(self.session)
        if not force and not await book.due(DUE, knobs.get("reflection.interval_hours")):
            return []

        await book.mark(DUE)
        values = await self.measures(knobs)
        beliefs = await self.beliefs()
        notes = await self.verify(beliefs, values, knobs)
        notes += await self.reflect(values, [b for b in beliefs if b.confidence >= knobs.get("reflection.drop_below")], knobs)
        await self.session.commit()

        if notes:
            logger.info("Reflexão: {}", "; ".join(notes))
        return notes

    async def summary(self, limit: int = 6) -> str:
        beliefs = sorted(await self.beliefs(), key=lambda b: -b.confidence)[:limit]
        lines = [
            f"- {b.confidence:.0%} {b.statement} → {b.action}" + (f" (confirmada {b.confirmed}x)" if b.confirmed else "") + (f" (contrariada {b.refuted}x)" if b.refuted else "")
            for b in beliefs
        ]
        return "Conclusões aprendidas (confiança):\n" + "\n".join(lines) if lines else ""
