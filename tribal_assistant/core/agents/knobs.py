"""Every number that gates a decision lives in the database and adjusts itself from how the last hours went."""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

WINDOW_HOURS = 6
MIN_ROUNDS = 10
STEP = 0.15
HISTORY = 30


@dataclass
class Metrics:
    """Shares of coordination rounds in the window where each situation happened."""

    rounds: int = 0
    idle_queue: float = 0.0
    recruit_starved: float = 0.0
    stock_empty: float = 0.0
    storage_full: float = 0.0
    pop_locked: float = 0.0
    scavenge_idle: float = 0.0
    raids_vetoed: float = 0.0
    raids_lost: float = 0.0
    no_targets: float = 0.0
    threatened: float = 0.0
    nothing_to_do: dict[str, float] = field(default_factory=dict)


Rule = Callable[[Metrics], tuple[int, str] | None]


@dataclass(frozen=True)
class KnobSpec:
    default: float
    description: str
    rule: Rule | None = None
    share: bool = False
    integer: bool = False


def more_when(metric: str, above: float, why: str) -> Rule:
    return lambda m: (+1, f"{why} ({getattr(m, metric):.0%})") if getattr(m, metric) > above else None


def less_when(metric: str, above: float, why: str) -> Rule:
    return lambda m: (-1, f"{why} ({getattr(m, metric):.0%})") if getattr(m, metric) > above else None


def either(*rules: Rule) -> Rule:
    def rule(m: Metrics) -> tuple[int, str] | None:
        for candidate in rules:
            result = candidate(m)
            if result:
                return result
        return None

    return rule


def cooldown(action: str) -> Rule:
    """Wait longer between checks that keep finding nothing, shorter when they keep finding work."""

    def rule(m: Metrics) -> tuple[int, str] | None:
        empty = m.nothing_to_do.get(action)
        if empty is None:
            return None
        if empty > 0.7:
            return +1, f"{action} sem nada a fazer em {empty:.0%} das tentativas"
        if empty < 0.2:
            return -1, f"{action} encontrou trabalho em {1 - empty:.0%} das tentativas"
        return None

    return rule


class Knobs:
    SPECS: ClassVar[dict[str, KnobSpec]] = {
        "base_stock_share": KnobSpec(
            0.25,
            "fração do estoque que a reserva mínima pode segurar",
            either(more_when("stock_empty", 0.3, "estoque quase zerado"), less_when("recruit_starved", 0.3, "recrutamento sem recurso")),
            share=True,
        ),
        "filler_wait_hours": KnobSpec(0.75, "espera da próxima obra do plano antes de encaixar uma obra que já cabe", less_when("idle_queue", 0.3, "fila de obras parada")),
        "scavenge_share": KnobSpec(
            0.4,
            "fração da população máxima em lanceiros para a coleta",
            either(less_when("pop_locked", 0.2, "população travada"), more_when("scavenge_idle", 0.3, "coleta sem tropas")),
            share=True,
        ),
    }

    def __init__(self, values: dict[str, float] | None = None) -> None:
        self.values = dict(values or {})

    def get(self, name: str) -> float:
        if name in self.values:
            return self.values[name]
        return self.SPECS[name].default

    def int(self, name: str) -> int:
        return max(1, round(self.get(name)))

    @classmethod
    def step(cls, name: str, value: float, direction: int) -> float:
        spec = cls.SPECS[name]
        changed = value * (1 + STEP) if direction > 0 else value * (1 - STEP)
        if spec.integer:
            changed = max(1, round(changed) if round(changed) != round(value) else round(value) + direction)
        if spec.share:
            changed = min(1.0, changed)
        return round(max(changed, 1e-6), 4)


def knob(view: Any, name: str) -> float:
    knobs = getattr(view, "knobs", None)
    return (knobs if isinstance(knobs, Knobs) else Knobs()).get(name)


class KnobStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self) -> Knobs:
        from tribal_assistant.core.models.knob import TuningKnob

        rows = (await self.session.execute(select(TuningKnob))).scalars().all()
        return Knobs({r.name: r.value for r in rows if r.name in Knobs.SPECS})

    async def rows(self) -> list[dict[str, Any]]:
        from tribal_assistant.core.models.knob import TuningKnob

        stored = {r.name: r for r in (await self.session.execute(select(TuningKnob))).scalars().all()}
        items = []
        for name, spec in Knobs.SPECS.items():
            row = stored.get(name)
            items.append(
                {
                    "name": name,
                    "description": spec.description,
                    "default": spec.default,
                    "value": row.value if row else spec.default,
                    "reason": row.reason if row else "",
                    "updated_at": row.updated_at.isoformat() if row else None,
                    "history": json.loads(row.history) if row else [],
                    "self_tuning": spec.rule is not None,
                }
            )
        return items

    async def set(self, name: str, value: float, reason: str) -> None:
        from tribal_assistant.core.models.knob import TuningKnob

        now = datetime.now(UTC).replace(tzinfo=None)
        row = (await self.session.execute(select(TuningKnob).where(TuningKnob.name == name))).scalar_one_or_none()
        if row is None:
            row = TuningKnob(name=name, value=value, reason=reason, history="[]", updated_at=now)
            self.session.add(row)

        history = json.loads(row.history or "[]")
        history.append({"at": now.isoformat(timespec="minutes"), "from": row.value, "to": value, "why": reason})
        row.value, row.reason, row.updated_at, row.history = value, reason, now, json.dumps(history[-HISTORY:], ensure_ascii=False)

    async def metrics(self) -> Metrics:
        from tribal_assistant.core.models.agent import AgentDecision
        from tribal_assistant.core.models.coordination import CoordinationRound

        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=WINDOW_HOURS)
        rounds = (await self.session.execute(select(CoordinationRound.data).where(CoordinationRound.created_at >= since))).scalars().all()
        decisions = (
            await self.session.execute(
                select(AgentDecision.action, AgentDecision.ok, AgentDecision.result).where(AgentDecision.created_at >= since, AgentDecision.dry_run.is_(False))
            )
        ).all()
        return Tuner.measure([json.loads(r) if isinstance(r, str) else (r or {}) for r in rounds], [tuple(d) for d in decisions])


class Tuner:
    """Measure the window, move every knob one step in the direction its rule asks, store the reason."""

    NOTHING = ("nenhum", "nenhuma", "nada", "já tem", "já está", "indisponível", "sem ")

    def __init__(self, session: AsyncSession) -> None:
        self.store = KnobStore(session)
        self.session = session

    @classmethod
    def measure(cls, rounds: list[dict[str, Any]], decisions: list[tuple[str, bool, str]] | None = None) -> Metrics:
        metrics = Metrics(rounds=len(rounds))
        if rounds:
            counts: dict[str, int] = {}
            for data in rounds:
                texts = " | ".join(str(i.get("text", "")) for i in data.get("insights") or [])
                deferred = data.get("deferred") or []
                whys = [(str(d.get("action")), str(d.get("why", ""))) for d in deferred]
                stock = (data.get("budget") or {}).get("stock") or {}
                storage = next((i.get("value") for i in data.get("insights") or [] if i.get("key") == "storage"), None)
                flags = {
                    "idle_queue": "fila de obras: 0 ordem" in texts,
                    "recruit_starved": any(a == "recruit_units" and w.startswith(("faltam", "consumiria")) for a, w in whys),
                    "stock_empty": bool(stock) and min(stock.values()) < 50,
                    "storage_full": "enche o armazém em 0." in texts or "armazém enche em 0." in texts or bool(storage),
                    "pop_locked": "população quase no limite" in texts or any("falta população" in w for _, w in whys),
                    "scavenge_idle": "coleta parada" in texts,
                    "raids_vetoed": any(a == "send_farm_attack" and w.startswith("vetado") for a, w in whys),
                    "no_targets": "nenhuma bárbara" in texts,
                    "threatened": "ATAQUES CHEGANDO" in texts or "ataque chegando" in texts,
                }
                for name, hit in flags.items():
                    counts[name] = counts.get(name, 0) + int(hit)
            for name, hits in counts.items():
                setattr(metrics, name, hits / len(rounds))

        attempts: dict[str, list[bool]] = {}
        for action, ok, result in decisions or []:
            text = str(result or "").lower()
            if action == "send_farm_attack" and ok is False:
                attempts.setdefault("_raids", []).append(True)
            attempts.setdefault(action, []).append(any(word in text for word in cls.NOTHING) and not ok)
        raids = [ok for action, ok, _ in decisions or [] if action == "send_farm_attack"]
        if raids:
            metrics.raids_lost = sum(1 for ok in raids if not ok) / len(raids)
        metrics.nothing_to_do = {a: sum(v) / len(v) for a, v in attempts.items() if not a.startswith("_") and len(v) >= 3}
        return metrics

    @staticmethod
    def plan(knobs: Knobs, metrics: Metrics) -> list[tuple[str, float, str]]:
        if metrics.rounds < MIN_ROUNDS:
            return []

        changes = []
        for name, spec in Knobs.SPECS.items():
            if spec.rule is None:
                continue
            verdict = spec.rule(metrics)
            if verdict is None:
                continue
            direction, why = verdict
            current = knobs.get(name)
            value = Knobs.step(name, current, direction)
            if value != current:
                changes.append((name, value, why))
        return changes

    async def run(self) -> list[tuple[str, float, str]]:
        knobs = await self.store.load()
        changes = self.plan(knobs, await self.store.metrics())
        for name, value, why in changes:
            await self.store.set(name, value, why)
        await self.session.commit()
        return changes
