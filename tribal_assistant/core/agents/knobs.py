"""Every number that gates a decision lives in the database and adjusts itself from how the last hours went."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knob_catalog import CATALOG
from tribal_assistant.core.agents.knob_rules import (
    KnobSpec,
    Metrics,
    Rule,
    cooldown,
    either,
    less_when,
    more_when,
    settle,
)

__all__ = ["KnobSpec", "KnobStore", "Knobs", "Metrics", "Rule", "Tuner", "cooldown", "either", "knob", "knob_int", "less_when", "more_when", "settle", "tuning"]

WINDOW_HOURS = 6
MIN_ROUNDS = 10
STEP = 0.15
HISTORY = 30


class Knobs:
    SPECS: ClassVar[dict[str, KnobSpec]] = CATALOG

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

    @classmethod
    def toward(cls, name: str, value: float, direction: int) -> float:
        """One step up or down; direction 0 walks back to the default without passing it."""
        if direction:
            return cls.step(name, value, direction)
        default = cls.SPECS[name].default
        if value == default or default <= 0:
            return value
        moved = cls.step(name, value, 1 if default > value else -1)
        return min(moved, default) if default > value else max(moved, default)


def tuning(source: Any) -> Knobs:
    """The knobs a view, a village context, a policy or a toolbox carries; defaults when none."""
    for holder in (source, getattr(source, "policy", None), getattr(getattr(source, "ctx", None), "policy", None)):
        knobs = getattr(holder, "knobs", None)
        if isinstance(knobs, Knobs):
            return knobs
    return Knobs()


def knob(source: Any, name: str) -> float:
    return tuning(source).get(name)


def knob_int(source: Any, name: str) -> int:
    return tuning(source).int(name)


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
                    "no_targets": "nenhuma bárbara" in texts.replace("nenhuma bárbara no raio longe o bastante", ""),
                    "threatened": "ATAQUES CHEGANDO" in texts or "ataque chegando" in texts,
                    "iron_short": any(w.startswith("faltam") and " iron" in w for a, w in whys if a == "upgrade_building"),
                    "actions_capped": any(w == "limite de ações por rodada" for _, w in whys),
                    "dodge_stuck": "nenhuma bárbara no raio longe o bastante" in texts,
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
        probes = [str(result or "") for action, _, result in decisions or [] if action in ("send_farm_attack", "send_spy")]
        if probes:
            metrics.raids_capped = sum(1 for text in probes if "ataques por hora" in text) / len(probes)
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
            value = Knobs.toward(name, current, direction)
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
