"""What each executed proposal really yielded, measured afterwards from decisions, village snapshots and reports."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.models.report import Report
from tribal_assistant.core.models.snapshot import VillageSnapshot

RAIDS = ("send_farm_attack", "send_farm_template")
GROWTH = ("upgrade_building",)
ARMY = ("recruit_units",)
REFUSED = -1.0
FAILED = -0.5
LOST = -1.0
OK_BASE = 0.25
UNKNOWN = 0.5
HIGH_FACTOR = 0.5
MIN_SAMPLES = 4
FACTORS = ("urgency", "impact", "risk_avoided", "opportunity", "opportunity_cost", "uncertainty")


@dataclass
class RoundRecord:
    village_id: int
    at: datetime
    data: dict[str, Any]


@dataclass
class Evidence:
    snapshots: dict[int, list[tuple[datetime, int, int]]] = field(default_factory=dict)
    reports: dict[str, list[tuple[datetime, str, int]]] = field(default_factory=dict)

    def raid(self, target: str, at: datetime) -> float | None:
        found = [(result, haul) for when, result, haul in self.reports.get(target, []) if when > at]
        if not found:
            return None
        if any(result == "red" for result, _ in found):
            return LOST
        return 1.0 if any(haul > 0 for _, haul in found) else 0.0

    def grew(self, village_id: int, at: datetime, column: int) -> float | None:
        rows = self.snapshots.get(village_id, [])
        before = [row for row in rows if row[0] <= at]
        after = [row for row in rows if row[0] > at]
        if not before or not after:
            return None
        return 1.0 if after[-1][column] > before[-1][column] else 0.0

    def confirm(self, entry: dict[str, Any], village_id: int, at: datetime) -> float | None:
        action = str(entry.get("action") or "")
        if action in RAIDS:
            target = str((entry.get("arguments") or {}).get("target") or "")
            return self.raid(target, at) if target else None
        if action in GROWTH:
            return self.grew(village_id, at, 1)
        if action in ARMY:
            return self.grew(village_id, at, 2)
        return None


class Outcomes:
    def __init__(self, evidence: Evidence | None = None) -> None:
        self.evidence = evidence or Evidence()

    def value(self, entry: dict[str, Any], village_id: int, at: datetime) -> float | None:
        """-1 refused or lost, -0.5 failed, from 0.25 to 1 when done and confirmed by what happened afterwards."""
        result = str(entry.get("result") or "")
        if result.startswith("(simulação)"):
            return None
        if not entry.get("ok"):
            return REFUSED if result.startswith("RECUSADO") else FAILED

        confirmed = self.evidence.confirm(entry, village_id, at)
        if confirmed == LOST:
            return LOST
        return OK_BASE + (1 - OK_BASE) * (UNKNOWN if confirmed is None else confirmed)

    def valued(self, records: list[RoundRecord]) -> list[tuple[RoundRecord, dict[str, Any], float]]:
        items = []
        for record in records:
            for entry in record.data.get("executed") or []:
                value = self.value(entry, record.village_id, record.at)
                if value is not None:
                    items.append((record, entry, value))
        return items

    @staticmethod
    def mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 3)

    def yields(self, records: list[RoundRecord]) -> dict[str, float]:
        """Average value of the executed actions of every specialist with enough samples."""
        by_source: dict[str, list[float]] = defaultdict(list)
        for _, entry, value in self.valued(records):
            by_source[str(entry.get("source") or "")].append(value)
        return {source: self.mean(values) for source, values in by_source.items() if source and len(values) >= MIN_SAMPLES}

    def factor_gaps(self, records: list[RoundRecord]) -> dict[str, float]:
        """Per role and factor: value of proposals strong in the factor minus value of the weak ones."""
        split: dict[str, tuple[list[float], list[float]]] = defaultdict(lambda: ([], []))
        for record, entry, value in self.valued(records):
            role = str(record.data.get("mode") or "")
            factors = entry.get("factors") or {}
            for factor in FACTORS:
                high, low = split[f"{role}.{factor}"]
                (high if float(factors.get(factor) or 0) >= HIGH_FACTOR else low).append(value)
        return {key: round(self.mean(high) - self.mean(low), 3) for key, (high, low) in split.items() if len(high) >= MIN_SAMPLES and len(low) >= MIN_SAMPLES}

    def explore(self, records: list[RoundRecord]) -> tuple[int, float]:
        """How many explored actions were measured and how much better or worse they did than the usual choices."""
        explored, usual = [], []
        for _, entry, value in self.valued(records):
            (explored if entry.get("exploration") else usual).append(value)
        if not explored or not usual:
            return len(explored), 0.0
        return len(explored), round(self.mean(explored) - self.mean(usual), 3)

    @staticmethod
    def signature(data: dict[str, Any]) -> tuple[str, ...]:
        return tuple(sorted(str(e.get("title") or e.get("key") or "") for e in data.get("executed") or [] if e.get("ok")))

    @classmethod
    def streak(cls, history: list[dict[str, Any]]) -> int:
        """Rounds in a row, newest first, that executed the same non-empty set of actions."""
        if not history:
            return 0
        first = cls.signature(history[0])
        if not first:
            return 0
        count = 0
        for data in history:
            if cls.signature(data) != first:
                break
            count += 1
        return count

    @classmethod
    def repetition(cls, records: list[RoundRecord], rounds: int) -> float:
        """Share of rounds that belong to a run of at least `rounds` identical rounds on the same village."""
        if not records:
            return 0.0
        by_village: dict[int, list[RoundRecord]] = defaultdict(list)
        for record in sorted(records, key=lambda r: r.at):
            by_village[record.village_id].append(record)

        repeated = 0
        for series in by_village.values():
            run: list[tuple[str, ...]] = []
            for record in series:
                signature = cls.signature(record.data)
                run = [*run, signature] if run and signature and run[-1] == signature else [signature]
                if signature and len(run) == rounds:
                    repeated += rounds
                elif signature and len(run) > rounds:
                    repeated += 1
        return round(repeated / len(records), 3)


class OutcomeReader:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def evidence(self, since: datetime, lead_hours: float) -> Evidence:
        start = since - timedelta(hours=lead_hours)
        snapshots: dict[int, list[tuple[datetime, int, int]]] = defaultdict(list)
        rows = await self.session.execute(
            select(VillageSnapshot.village_id, VillageSnapshot.taken_at, VillageSnapshot.points, VillageSnapshot.troops_total)
            .where(VillageSnapshot.taken_at >= start)
            .order_by(VillageSnapshot.taken_at)
        )
        for village_id, taken_at, points, troops in rows.all():
            snapshots[village_id].append((taken_at, points, troops))

        reports: dict[str, list[tuple[datetime, str, int]]] = defaultdict(list)
        found = await self.session.execute(
            select(Report.target_coords, Report.received_at, Report.result, Report.haul_total, Report.loot_wood, Report.loot_clay, Report.loot_iron).where(
                Report.received_at >= since, Report.target_coords.is_not(None)
            )
        )
        for coords, received, result, haul, wood, clay, iron in found.all():
            reports[str(coords)].append((received, str(result or ""), haul if haul is not None else wood + clay + iron))
        return Evidence(dict(snapshots), dict(reports))
