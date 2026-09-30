"""Publishes each step of a coordination round as it happens, for the live flow on the panel."""

from datetime import UTC, datetime
from typing import Any

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.proposal import Proposal
from tribal_assistant.core.events import event_bus

KIND = "flow"


class FlowFeed:
    def __init__(self, ctx: VillageContext) -> None:
        self.village = {"village_id": ctx.id, "village": ctx.village.name, "coords": ctx.village.coords}

    def _publish(self, phase: str, **data: Any) -> None:
        event_bus.publish(KIND, {"phase": phase, **self.village, **data})

    @staticmethod
    def node(proposal: Proposal) -> dict[str, Any]:
        return {
            "key": proposal.key,
            "source": proposal.source,
            "action": proposal.action,
            "title": proposal.title(),
            "priority": round(proposal.priority, 1),
            "explored": proposal.explored,
        }

    def start(self, mode: str, role: str, specialists: list[dict[str, str]]) -> None:
        self._publish("start", mode=mode, role=role, specialists=specialists)

    def plan(self, ordered: list[Proposal]) -> None:
        self._publish("plan", proposals=[self.node(p) for p in ordered])

    def running(self, proposal: Proposal) -> None:
        self._publish("running", **self.node(proposal))

    def result(self, proposal: Proposal, ok: bool, text: str) -> None:
        self._publish("result", **self.node(proposal), ok=ok, text=text)

    def deferred(self, proposal: Proposal, why: str) -> None:
        self._publish("deferred", **self.node(proposal), why=why)

    def done(self, summary: str, executed: int, failed: int, deferred: int, next_review_at: datetime | None) -> None:
        review = (next_review_at if next_review_at.tzinfo else next_review_at.replace(tzinfo=UTC)).isoformat() if next_review_at else None
        self._publish("done", summary=summary, executed=executed, failed=failed, deferred=deferred, next_review_at=review)
