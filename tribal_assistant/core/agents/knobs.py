"""Every number that gates a decision lives in the database and adjusts itself from how the last hours went."""

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.coordination.outcomes import OutcomeReader, Outcomes, RoundRecord
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
from tribal_assistant.core.agents.social.ledger import SENDS, SocialLedger
from tribal_assistant.core.models.agent import AgentDecision
from tribal_assistant.core.models.coordination import CoordinationRound
from tribal_assistant.core.models.knob import TuningKnob
from tribal_assistant.core.repositories.frames import FrameRepository
from tribal_assistant.core.repositories.lessons import LessonRepository

__all__ = ["KnobSpec", "KnobStore", "Knobs", "Metrics", "Rule", "Tuner", "cooldown", "either", "knob", "knob_int", "less_when", "more_when", "settle", "tuning"]

WINDOW_HOURS = 6
MIN_ROUNDS = 10
STEP = 0.15
HISTORY = 30
BUCKET_MINUTES = 10
LAST_RUN = "tuning:last_run"
FARM_HAULS = re.compile(r"(\d+)/(\d+) relatórios com carga cheia")
RAIDS = ("send_farm_attack", "send_farm_template")


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
        rows = (await self.session.execute(select(TuningKnob))).scalars().all()
        return Knobs({r.name: r.value for r in rows if r.name in Knobs.SPECS})

    async def rows(self) -> list[dict[str, Any]]:
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
        now = datetime.now(UTC).replace(tzinfo=None)
        row = (await self.session.execute(select(TuningKnob).where(TuningKnob.name == name))).scalar_one_or_none()
        if row is None:
            row = TuningKnob(name=name, value=value, reason=reason, history="[]", updated_at=now)
            self.session.add(row)

        history = json.loads(row.history or "[]")
        history.append({"at": now.isoformat(timespec="minutes"), "from": row.value, "to": value, "why": reason})
        row.value, row.reason, row.updated_at, row.history = value, reason, now, json.dumps(history[-HISTORY:], ensure_ascii=False)

    async def updated(self) -> dict[str, datetime]:
        return {r.name: r.updated_at for r in (await self.session.execute(select(TuningKnob))).scalars().all()}

    async def metrics(self, since: datetime | None = None) -> Metrics:
        moment = datetime.now(UTC).replace(tzinfo=None)
        since = since or moment - timedelta(hours=WINDOW_HOURS)
        window = max((moment - since).total_seconds() / 3600, 1 / 60)
        rows = (
            await self.session.execute(
                select(CoordinationRound.village_id, CoordinationRound.created_at, CoordinationRound.data).where(CoordinationRound.created_at >= since)
            )
        ).all()
        records = [RoundRecord(village, at, json.loads(data) if isinstance(data, str) else (data or {})) for village, at, data in rows]
        decisions = (
            await self.session.execute(
                select(AgentDecision.action, AgentDecision.ok, AgentDecision.result).where(AgentDecision.created_at >= since, AgentDecision.dry_run.is_(False))
            )
        ).all()
        metrics = Tuner.measure([r.data for r in records], [tuple(d) for d in decisions])
        ledger = SocialLedger(self.session)
        metrics.contacts_unanswered = await ledger.unanswered_share() or 0.0
        metrics.builds_done = float(await FrameRepository(self.session).most_levels_gained(since))
        last = await ledger.last_social_action()
        metrics.social_idle = 1.0 if last is None else round(min(1.0, (moment - last).total_seconds() / 3600 / (await self.load()).get("tuner.window_hours")), 3)
        await self.learn(metrics, records, since, window)
        return metrics

    async def learn(self, metrics: Metrics, records: list[RoundRecord], since: datetime, window: float = WINDOW_HOURS) -> None:
        """What the executed proposals yielded afterwards, per specialist, per factor and for explorations."""
        knobs = await self.load()
        outcomes = Outcomes(await OutcomeReader(self.session).evidence(since, window), knobs.int("learning.min_samples"), knobs.get("learning.high_factor"))
        metrics.yields = outcomes.yields(records)
        metrics.factor_gaps = outcomes.factor_gaps(records)
        metrics.explored, metrics.explore_gap = outcomes.explore(records)
        metrics.repetition = Outcomes.repetition(records, knobs.int("coordinator.repeat_rounds"))


class Tuner:
    """Measure the window, move every knob one step in the direction its rule asks, store the reason."""

    NOTHING = ("nenhum", "nenhuma", "nada", "já tem", "já está", "indisponível", "sem ")

    def __init__(self, session: AsyncSession) -> None:
        self.store = KnobStore(session)
        self.lessons = LessonRepository(session)
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
                recruited = any(e.get("action") == "recruit_units" and e.get("ok") for e in data.get("executed") or [])
                idle = "fila de obras: 0 ordem" in texts
                flags = {
                    "idle_queue": idle,
                    "idle_recruiting": idle and recruited,
                    "army_stalled": not recruited,
                    "recruit_starved": any(a == "recruit_units" and w.startswith(("faltam", "consumiria")) for a, w in whys),
                    "stock_empty": bool(stock) and min(stock.values()) < 50,
                    "storage_full": "enche o armazém em 0." in texts or "armazém enche em 0." in texts or bool(storage),
                    "pop_locked": "população quase no limite" in texts or any("falta população" in w for _, w in whys),
                    "scavenge_idle": "coleta parada" in texts,
                    "raids_vetoed": any(a in RAIDS and w.startswith("vetado") for a, w in whys),
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
            metrics.farm_full, metrics.farm_partial = cls.farm_hauls(rounds)

        attempts: dict[str, list[bool]] = {}
        for action, ok, result in decisions or []:
            text = str(result or "").lower()
            if action in RAIDS and ok is False:
                attempts.setdefault("_raids", []).append(True)
            attempts.setdefault(action, []).append(any(word in text for word in cls.NOTHING) and not ok)
        raids = [ok for action, ok, _ in decisions or [] if action in RAIDS]
        if raids:
            metrics.raids_lost = sum(1 for ok in raids if not ok) / len(raids)
        probes = [str(result or "") for action, _, result in decisions or [] if action in (*RAIDS, "send_spy")]
        if probes:
            metrics.raids_capped = sum(1 for text in probes if "ataques por hora" in text) / len(probes)
        sends = [str(result or "") for action, _, result in decisions or [] if action in SENDS]
        if sends:
            metrics.mail_capped = sum(1 for text in sends if "mensagens por hora" in text) / len(sends)
        for action, name in (("send_noble", "nobles_failed"), ("send_resources", "shipments_failed")):
            sent = [ok for kind, ok, _ in decisions or [] if kind == action]
            if sent:
                setattr(metrics, name, sum(1 for ok in sent if not ok) / len(sent))
        metrics.nothing_to_do = {a: sum(v) / len(v) for a, v in attempts.items() if not a.startswith("_") and len(v) >= 3}
        return metrics

    @staticmethod
    def farm_hauls(rounds: list[dict[str, Any]]) -> tuple[float, float]:
        """Average share of farm assistant rows that came back full, and of those that did not."""
        shares = []
        for data in rounds:
            for insight in data.get("insights") or []:
                found = FARM_HAULS.search(str(insight.get("text", ""))) if insight.get("key") == "farm_hauls" else None
                if found and int(found.group(2)):
                    shares.append(int(found.group(1)) / int(found.group(2)))
        if not shares:
            return 0.0, 0.0
        full = sum(shares) / len(shares)
        return full, 1 - full

    @staticmethod
    def plan(knobs: Knobs, metrics: Metrics, names: set[str] | None = None, least: int = MIN_ROUNDS) -> list[tuple[str, float, str]]:
        if metrics.rounds < least:
            return []

        changes = []
        for name, spec in Knobs.SPECS.items():
            if spec.rule is None or (names is not None and name not in names):
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

    async def due(self, knobs: Knobs | None = None) -> bool:
        """At most one pass per tuned interval, however often the server restarts."""
        knobs = knobs or await self.store.load()
        row = await self.lessons.get(LAST_RUN)
        return row is None or datetime.now(UTC).replace(tzinfo=None) - row.last_seen >= timedelta(minutes=knobs.get("tuner.interval_minutes"))

    @staticmethod
    def since(updated: datetime | None, start: datetime) -> datetime:
        """A knob is judged only by the rounds played under its current value, bucketed so knobs share a measurement."""
        moment = max(updated or start, start)
        return moment.replace(minute=moment.minute - moment.minute % BUCKET_MINUTES, second=0, microsecond=0)

    async def run(self, force: bool = False) -> list[tuple[str, float, str]]:
        knobs = await self.store.load()
        if not force and not await self.due(knobs):
            return []

        await self.lessons.observe(LAST_RUN, "tuning", "Último ajuste automático", commit=False)
        start = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=knobs.get("tuner.window_hours"))
        updated = await self.store.updated()

        groups: dict[datetime, set[str]] = {}
        for name, spec in Knobs.SPECS.items():
            if spec.rule is not None:
                groups.setdefault(self.since(updated.get(name), start), set()).add(name)

        changes = []
        for since, names in sorted(groups.items()):
            changes += self.plan(knobs, await self.store.metrics(since), names, knobs.int("tuner.min_rounds"))

        for name, value, why in changes:
            await self.store.set(name, value, why)
        await self.session.commit()
        return changes
