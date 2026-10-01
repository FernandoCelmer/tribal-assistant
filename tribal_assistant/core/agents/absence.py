"""The bot's sense of being away: a heartbeat every round, what a gap cost on return, and when the next stop usually comes."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.clock import Clock
from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.knobs import knob
from tribal_assistant.core.game.scraper.game import SERVER_TZ
from tribal_assistant.core.models.agent import AgentRun
from tribal_assistant.core.models.report import Report
from tribal_assistant.core.models.snapshot import VillageSnapshot
from tribal_assistant.core.repositories.lessons import LessonRepository

RESOURCES = {"wood": "madeira", "clay": "argila", "iron": "ferro"}
HISTORY = 40
MIN_PATTERN = 3


def _latest(values: list[Any]) -> str | None:
    moments = [m for m in (Clock.aware(v) for v in values) if m]
    return max(moments).isoformat() if moments else None


@dataclass
class Gap:
    start: datetime
    end: datetime
    queue_idle: float = 0.0
    scavenge_idle: float = 0.0
    recruit_idle: float = 0.0
    wasted: dict[str, int] = field(default_factory=dict)
    full_at: datetime | None = None
    reports: dict[str, int] = field(default_factory=dict)
    attacked: int = 0
    points: tuple[int, int] = (0, 0)

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600

    def describe(self, clock: Clock) -> str:
        lines = [f"AUSÊNCIA: o bot ficou {clock.span(self.hours * 3600)} sem jogar (de {clock.local(self.start)} até {clock.local(self.end)})."]

        lost = []
        if self.queue_idle >= 0.25:
            lost.append(f"fila de obras parada {clock.span(self.queue_idle * 3600)}")
        if self.scavenge_idle >= 0.25:
            lost.append(f"coleta parada {clock.span(self.scavenge_idle * 3600)}")
        if self.recruit_idle >= 0.25:
            lost.append(f"recrutamento parado {clock.span(self.recruit_idle * 3600)}")
        if self.wasted:
            spilled = ", ".join(f"{RESOURCES[k]} ~{v}" for k, v in self.wasted.items())
            lost.append(f"armazém lotou {clock.local(self.full_at)} e desperdiçou {spilled}")
        if lost:
            lines.append("Perdido: " + " · ".join(lost) + ".")

        seen = []
        if self.attacked:
            seen.append(f"{self.attacked} ataque(s) contra a aldeia")
        if self.reports:
            seen.append("relatórios: " + ", ".join(f"{n} {k}" for k, n in self.reports.items()))
        if self.points[0] != self.points[1]:
            seen.append(f"pontos {self.points[0]}→{self.points[1]}")
        if seen:
            lines.append("Enquanto isso: " + " · ".join(seen) + ".")

        lines.append("Agora: encher a fila, mandar a coleta, gastar o que está perto do teto e rever o plano.")
        return "\n".join(lines)

    def record(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "hours": round(self.hours, 2),
            "queue_idle": round(self.queue_idle, 2),
            "wasted": self.wasted,
            "attacked": self.attacked,
        }


class Heartbeat:
    """What a village looked like at one round, enough to judge a gap that starts right after it."""

    @staticmethod
    def of(ctx: VillageContext, now: datetime) -> dict[str, Any]:
        v = ctx.village
        return {
            "at": now.isoformat(),
            "queue_until": _latest([q["until"] for q in ctx.queue]),
            "queue_size": len(ctx.queue),
            "scavenge_back": _latest([o.return_at for o in v.scavenge if not o.is_locked]),
            "scavenge_open": sum(1 for o in v.scavenge if not o.is_locked),
            "recruit_until": _latest([r.finishes_at for r in v.recruit_orders]),
            "stock": dict(ctx.stock),
            "storage": v.storage,
            "prod": {"wood": v.wood_prod, "clay": v.clay_prod, "iron": v.iron_prod},
            "points": v.points,
        }

    @staticmethod
    def idle(until: str | None, start: datetime, end: datetime) -> float:
        busy = Clock.aware(until) or start
        return max(0.0, (end - max(busy, start)).total_seconds() / 3600)

    @classmethod
    def gap(cls, beat: dict[str, Any], now: datetime, points: int) -> Gap:
        start = Clock.aware(beat["at"]) or now
        hours = (now - start).total_seconds() / 3600
        gap = Gap(start=start, end=now, points=(int(beat.get("points") or points), points))

        if not beat.get("partial"):
            gap.queue_idle = cls.idle(beat.get("queue_until"), start, now)
            if beat.get("scavenge_open"):
                gap.scavenge_idle = cls.idle(beat.get("scavenge_back"), start, now)
            gap.recruit_idle = cls.idle(beat.get("recruit_until"), start, now)

        storage = int(beat.get("storage") or 0)
        for key, stock in (beat.get("stock") or {}).items():
            prod = int((beat.get("prod") or {}).get(key) or 0)
            if prod <= 0 or not storage:
                continue
            fill = max(0.0, (storage - int(stock)) / prod)
            if fill < hours:
                gap.wasted[key] = int(prod * (hours - fill))
                full = start + timedelta(hours=fill)
                gap.full_at = min(gap.full_at, full) if gap.full_at else full

        return gap


class Habit:
    """When the bot usually stops and for how long, read from the gaps it lived through."""

    def __init__(self, history: list[dict[str, Any]], least_hours: float) -> None:
        self.gaps = [g for g in history if float(g.get("hours") or 0) >= least_hours]

    @staticmethod
    def _minutes_from_noon(moment: datetime) -> int:
        local = moment.astimezone(SERVER_TZ)
        return (local.hour * 60 + local.minute - 12 * 60) % (24 * 60)

    def forecast(self, now: datetime) -> tuple[datetime, float, int] | None:
        if len(self.gaps) < MIN_PATTERN:
            return None

        starts = [self._minutes_from_noon(Clock.aware(g["start"])) for g in self.gaps]
        offset = int(median(starts))
        hours = float(median(float(g["hours"]) for g in self.gaps))

        local = now.astimezone(SERVER_TZ)
        noon = local.replace(hour=12, minute=0, second=0, microsecond=0)
        if local.hour < 12:
            noon -= timedelta(days=1)
        stop = noon + timedelta(minutes=offset)
        if stop + timedelta(hours=hours) < local:
            stop += timedelta(days=1)

        return stop.astimezone(UTC), hours, len(self.gaps)


class Absence:
    """Reads the last heartbeat of each village at the start of a round and turns a long gap into context and lessons."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LessonRepository(session)

    async def observe(self, ctx: VillageContext, interval_minutes: float, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        clock = Clock(now)
        key = f"presence:{ctx.id}"
        row = await self.repo.get(key)
        beat = json.loads(row.data or "{}") if row else await self._last_known(ctx)

        if beat.get("at"):
            gap = Heartbeat.gap(beat, now, ctx.village.points)
            if gap.hours * 60 >= max(knob(ctx, "absence.min_minutes"), 3 * interval_minutes):
                await self._learn(ctx, gap)
                ctx.absence_new = True

        await self.repo.observe(key, "presence", f"última rodada em {ctx.village.coords}", "", Heartbeat.of(ctx, now), commit=False)
        await self.session.commit()
        await self.attach(ctx, clock)

    async def _last_known(self, ctx: VillageContext) -> dict[str, Any]:
        """Before the first heartbeat: the last finished round and the village snapshot taken before it."""
        ended = await self.session.scalar(select(func.max(AgentRun.finished_at)).where(AgentRun.status.not_in(("running", "interrupted"))))
        if ended is None:
            return {}

        snap = await self.session.scalar(
            select(VillageSnapshot)
            .where(VillageSnapshot.village_id == ctx.id, VillageSnapshot.taken_at <= ended)
            .order_by(VillageSnapshot.taken_at.desc())
            .limit(1)
        )
        if snap is None:
            return {"at": ended.replace(tzinfo=UTC).isoformat(), "partial": True}

        return {
            "at": ended.replace(tzinfo=UTC).isoformat(),
            "partial": True,
            "stock": {"wood": snap.wood, "clay": snap.clay, "iron": snap.iron},
            "storage": snap.storage,
            "prod": {"wood": snap.wood_prod, "clay": snap.clay_prod, "iron": snap.iron_prod},
            "points": snap.points,
        }

    async def _learn(self, ctx: VillageContext, gap: Gap) -> None:
        naive = (gap.start.replace(tzinfo=None), gap.end.replace(tzinfo=None))
        rows = await self.session.execute(
            select(Report.category, func.count(Report.id)).where(Report.received_at >= naive[0], Report.received_at <= naive[1]).group_by(Report.category)
        )
        gap.reports = {category: count for category, count in rows.all() if count}
        gap.attacked = int(
            await self.session.scalar(
                select(func.count(Report.id)).where(
                    Report.received_at >= naive[0],
                    Report.received_at <= naive[1],
                    Report.category == "attack",
                    Report.target_coords == ctx.village.coords,
                )
            )
            or 0
        )

        text = gap.describe(Clock(gap.end))
        await self.repo.observe(f"absence:{ctx.id}", "absence", f"ausência de {gap.hours:.1f}h em {ctx.village.coords}", text, {**gap.record(), "text": text}, commit=False)

        history = await self.repo.get("absence:history")
        past = json.loads(history.data or "{}").get("gaps", []) if history else []
        await self.repo.observe("absence:history", "absence", "ausências do bot", "", {"gaps": [*past, gap.record()][-HISTORY:]}, commit=False)

    async def attach(self, ctx: VillageContext, clock: Clock | None = None) -> None:
        clock = clock or Clock()
        row = await self.repo.get(f"absence:{ctx.id}")
        if row is not None:
            data = json.loads(row.data or "{}")
            ended = Clock.aware(data.get("end"))
            if ended and (clock.now - ended).total_seconds() / 3600 <= knob(ctx, "absence.recall_hours"):
                ctx.absence = f"{data.get('text', '')}\n(volta {clock.relative(ended)})"

        history = await self.repo.get("absence:history")
        gaps = json.loads(history.data or "{}").get("gaps", []) if history else []
        forecast = Habit(gaps, knob(ctx, "absence.habit_hours")).forecast(clock.now)
        if forecast is None:
            return

        stop, hours, count = forecast
        ahead = (stop - clock.now).total_seconds() / 60
        if 0 <= ahead <= knob(ctx, "absence.prepare_minutes"):
            ctx.absence_soon = (
                f"PARADA PROVÁVEL {clock.when(stop)} por ~{clock.span(hours * 3600)} (padrão de {count} ausências): "
                "antes dela, obras longas na fila, coleta mais longa, recrutamento que dure a noite e estoque gasto."
            )
