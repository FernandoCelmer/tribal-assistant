"""Queries behind the agents dashboard, plus retention of old traces."""

import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.models.agent import AgentDecision, AgentRun, AgentStep
from tribal_assistant.core.models.log import AppLog
from tribal_assistant.core.models.village import Village

LEVELS = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
ACTION_GROUPS = {
    "send_farm_attack": "attacks",
    "send_farm_template": "attacks",
    "upgrade_building": "builds",
    "recruit_units": "recruits",
    "complete_quest": "quests",
    "claim_quest_rewards": "quests",
}


class ObservabilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    async def runs(self, limit: int = 30) -> Sequence[AgentRun]:
        stmt = select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
        return (await self.session.execute(stmt)).scalars().all()

    async def run(self, run_id: str) -> AgentRun | None:
        stmt = select(AgentRun).where(AgentRun.run_id == run_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def steps(self, run_id: str) -> Sequence[AgentStep]:
        stmt = select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.seq)
        return (await self.session.execute(stmt)).scalars().all()

    async def decisions(self, run_id: str) -> Sequence[AgentDecision]:
        stmt = (
            select(AgentDecision)
            .where(AgentDecision.run_id == run_id, AgentDecision.action != "summary")
            .order_by(AgentDecision.id)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def village_names(self) -> dict[int, str]:
        rows = (await self.session.execute(select(Village.id, Village.name, Village.coords))).all()
        return {row.id: f"{row.name} ({row.coords})" for row in rows}

    async def stats(self, hours: int) -> dict:
        since = self.now() - timedelta(hours=hours)

        runs = (await self.session.execute(select(AgentRun).where(AgentRun.started_at >= since))).scalars().all()
        decisions = (
            await self.session.execute(
                select(AgentDecision).where(
                    AgentDecision.created_at >= since, AgentDecision.action != "summary"
                )
            )
        ).scalars().all()

        buckets: dict[datetime, Counter] = defaultdict(Counter)
        start = since.replace(minute=0, second=0, microsecond=0)
        for offset in range(hours + 1):
            buckets[start + timedelta(hours=offset)]

        refusals: Counter = Counter()
        by_action: Counter = Counter()
        groups: Counter = Counter()
        per_agent: dict[str, dict] = {}

        for d in decisions:
            refused = d.result.startswith("RECUSADO")
            hour = d.created_at.replace(minute=0, second=0, microsecond=0)
            buckets[hour][d.agent] += 1
            by_action[d.action] += 1

            if refused:
                refusals[self._reason(d.result)] += 1
            elif d.ok and not d.dry_run and d.action in ACTION_GROUPS:
                groups[ACTION_GROUPS[d.action]] += 1

            stat = per_agent.setdefault(
                d.agent,
                {"agent": d.agent, "actions": 0, "ok": 0, "refused": 0, "failed": 0,
                 "last_action": None, "last_result": None, "last_at": None},
            )
            stat["actions"] += 1
            stat["refused" if refused else ("ok" if d.ok else "failed")] += 1
            if stat["last_at"] is None or d.created_at > stat["last_at"]:
                stat.update(last_action=d.action, last_result=d.result, last_at=d.created_at)

        return {
            "hours": hours,
            "runs": len(runs),
            "runs_failed": sum(1 for r in runs if r.status == "failed"),
            "actions_ok": sum(r.actions_ok for r in runs),
            "actions_refused": sum(r.actions_refused for r in runs),
            "actions_failed": sum(r.actions_failed for r in runs),
            "attacks": groups["attacks"],
            "builds": groups["builds"],
            "recruits": groups["recruits"],
            "quests": groups["quests"],
            "tokens_in": sum(r.tokens_in for r in runs),
            "tokens_out": sum(r.tokens_out for r in runs),
            "hourly": [{"hour": h, "by_agent": dict(c)} for h, c in sorted(buckets.items())],
            "refusals": [{"label": k, "count": v} for k, v in refusals.most_common(8)],
            "by_action": [{"label": k, "count": v} for k, v in by_action.most_common()],
            "agents": sorted(per_agent.values(), key=lambda s: s["agent"]),
        }

    @staticmethod
    def _reason(result: str) -> str:
        text = result.removeprefix("RECUSADO:").strip()
        text = re.sub(r"\d+\|\d+", "alvo", text)
        text = re.sub(r"\d+(\.\d+)?", "N", text)
        return text[:80]

    async def flow(self, hours: int, run_id: str | None = None) -> dict:
        stmt = select(AgentStep).where(AgentStep.kind == "tool_result")

        if run_id:
            stmt = stmt.where(AgentStep.run_id == run_id)
        else:
            stmt = stmt.where(AgentStep.created_at >= self.now() - timedelta(hours=hours))

        steps = (await self.session.execute(stmt)).scalars().all()

        agent_tool: Counter = Counter()
        tool_outcome: Counter = Counter()
        agents: Counter = Counter()
        tools: Counter = Counter()

        for step in steps:
            tool = step.tool or "?"
            outcome = self._outcome(step)
            agent_tool[(step.agent, tool)] += 1
            tool_outcome[(tool, outcome)] += 1
            agents[step.agent] += 1
            tools[tool] += 1

        outcomes = Counter()
        for (_, outcome), count in tool_outcome.items():
            outcomes[outcome] += count

        return {
            "calls": len(steps),
            "runs": len({s.run_id for s in steps}),
            "agents": [{"id": k, "count": v} for k, v in agents.most_common()],
            "tools": [{"id": k, "count": v} for k, v in tools.most_common()],
            "outcomes": [{"id": k, "count": v} for k, v in outcomes.most_common()],
            "agent_tool": [{"source": a, "target": t, "count": c} for (a, t), c in agent_tool.most_common()],
            "tool_outcome": [{"source": t, "target": o, "count": c} for (t, o), c in tool_outcome.most_common()],
        }

    @staticmethod
    def _outcome(step: AgentStep) -> str:
        if step.content.startswith("RECUSADO"):
            return "refused"
        if step.is_error:
            return "failed"
        return "ok"

    async def active_run(self, within_minutes: int = 15) -> AgentRun | None:
        since = self.now() - timedelta(minutes=within_minutes)
        stmt = (
            select(AgentRun)
            .where(AgentRun.status == "running", AgentRun.started_at >= since)
            .order_by(AgentRun.started_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def interrupt_stale(self, older_than_minutes: int = 0) -> int:
        cutoff = self.now() - timedelta(minutes=older_than_minutes)
        rows = (
            await self.session.execute(
                select(AgentRun).where(AgentRun.status == "running", AgentRun.started_at <= cutoff)
            )
        ).scalars().all()

        for run in rows:
            run.status = "interrupted"
            run.error = run.error or "processo encerrado antes do fim da rodada"
            run.finished_at = run.finished_at or self.now()

        await self.session.commit()
        return len(rows)

    async def logs(
        self,
        level: str = "INFO",
        limit: int = 200,
        query: str | None = None,
        before_id: int | None = None,
    ) -> Sequence[AppLog]:
        allowed = LEVELS[LEVELS.index(level.upper()) :] if level.upper() in LEVELS else LEVELS
        stmt = select(AppLog).where(AppLog.level.in_(allowed)).order_by(AppLog.id.desc()).limit(limit)

        if query:
            stmt = stmt.where(AppLog.message.ilike(f"%{query}%"))
        if before_id:
            stmt = stmt.where(AppLog.id < before_id)

        return (await self.session.execute(stmt)).scalars().all()

    async def prune(self, days: int) -> int:
        cutoff = self.now() - timedelta(days=days)
        removed = 0

        for model, column in (
            (AgentStep, AgentStep.created_at),
            (AgentDecision, AgentDecision.created_at),
            (AgentRun, AgentRun.started_at),
        ):
            result = await self.session.execute(delete(model).where(column < cutoff))
            removed += result.rowcount or 0

        await self.session.commit()
        return removed
