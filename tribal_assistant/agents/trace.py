"""Records a whole agent round: the run row, every step, live status and dashboard events."""

from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.events import event_bus
from tribal_assistant.models.agent import AgentRun, AgentStep

MAX_CONTENT = 20_000


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RunTrace:
    """One per round. Steps are numbered in order and published as they happen."""

    live: ClassVar[dict[str, Any] | None] = None

    def __init__(
        self,
        session: AsyncSession,
        *,
        run_id: str,
        trigger: str,
        brain: str,
        provider: str | None,
        model: str | None,
        dry_run: bool,
    ) -> None:
        self.session = session
        self.run = AgentRun(
            run_id=run_id,
            trigger=trigger,
            status="running",
            brain=brain,
            provider=provider,
            model=model,
            dry_run=dry_run,
            started_at=_now(),
        )
        self.seq = 0
        self.village_id: int | None = None
        self.village_label = ""
        self.agent = ""

    @property
    def run_id(self) -> str:
        return self.run.run_id

    async def start(self) -> None:
        self.session.add(self.run)
        await self.session.commit()

        RunTrace.live = {"run_id": self.run_id, "started_at": self.run.started_at.isoformat(), "village": None, "agent": None, "step": "iniciando"}
        event_bus.publish("run_started", self._run_payload())

    def focus(self, village_id: int | None, village_label: str, agent: str) -> None:
        self.village_id = village_id
        self.village_label = village_label
        self.agent = agent

        if RunTrace.live is not None:
            RunTrace.live.update({"village": village_label, "agent": agent, "step": "pensando"})

    async def step(self, kind: str, content: str, *, tool: str | None = None, is_error: bool = False) -> None:
        self.seq += 1
        row = AgentStep(
            run_id=self.run_id,
            village_id=self.village_id,
            agent=self.agent or "runner",
            seq=self.seq,
            kind=kind,
            tool=tool,
            content=content[:MAX_CONTENT],
            is_error=is_error,
        )
        self.session.add(row)
        await self.session.commit()

        if RunTrace.live is not None:
            RunTrace.live["step"] = f"{kind}{f' {tool}' if tool else ''}"

        event_bus.publish(
            "step",
            {
                "run_id": self.run_id,
                "seq": self.seq,
                "village": self.village_label,
                "agent": row.agent,
                "kind": kind,
                "tool": tool,
                "content": content[:600],
                "is_error": is_error,
            },
        )

    def count(self, ok: bool, refused: bool) -> None:
        if refused:
            self.run.actions_refused += 1
        elif ok:
            self.run.actions_ok += 1
        else:
            self.run.actions_failed += 1

    def usage(self, tokens_in: int, tokens_out: int) -> None:
        self.run.tokens_in += tokens_in
        self.run.tokens_out += tokens_out

    async def finish(self, *, villages: int, status: str = "done", error: str | None = None) -> None:
        self.run.villages = villages
        self.run.status = status
        self.run.error = error
        self.run.finished_at = _now()
        await self.session.commit()

        RunTrace.live = None
        event_bus.publish("run_finished", self._run_payload())

    def _run_payload(self) -> dict[str, Any]:
        r = self.run
        return {
            "run_id": r.run_id,
            "status": r.status,
            "trigger": r.trigger,
            "brain": r.brain,
            "model": r.model,
            "dry_run": r.dry_run,
            "villages": r.villages,
            "actions_ok": r.actions_ok,
            "actions_refused": r.actions_refused,
            "actions_failed": r.actions_failed,
            "tokens_in": r.tokens_in,
            "tokens_out": r.tokens_out,
            "error": r.error,
        }
