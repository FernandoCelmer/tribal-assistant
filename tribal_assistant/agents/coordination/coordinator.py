"""Turns proposals into an executed plan: role and mode, reservations, vetoes, scores, deferrals."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from tribal_assistant.agents.coordination.budget import Budget, Reservation
from tribal_assistant.agents.coordination.constraints import Constraint
from tribal_assistant.agents.coordination.insight import now
from tribal_assistant.agents.coordination.proposal import Proposal
from tribal_assistant.agents.coordination.strategy import GOALS, LABELS, WEIGHTS, Role
from tribal_assistant.agents.coordination.view import CoordinationView

Execute = Callable[[Proposal], Awaitable[tuple[bool, str]]]
MAX_ACTIONS = 10
BUILD_ACTIONS = ("upgrade_building",)


@dataclass
class Decision:
    role: Role
    mode: Role
    goal: str
    executed: list[dict[str, Any]] = field(default_factory=list)
    deferred: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    budget: Budget | None = None
    next_review_at: datetime | None = None

    def next_action(self) -> dict[str, Any] | None:
        done = [e for e in self.executed if e["ok"]]
        if done:
            return done[0]

        return self.deferred[0] if self.deferred else None

    def summary(self) -> str:
        ok = [e["title"] for e in self.executed if e["ok"]]
        parts = [f"modo {LABELS[self.mode]}"]
        parts.append(f"feito: {', '.join(ok)}" if ok else "nada executado")
        if self.deferred:
            parts.append(f"{len(self.deferred)} adiada(s), 1ª: {self.deferred[0]['title']} ({self.deferred[0]['why']})")

        return "; ".join(parts)

    def to_dict(self, insights: list[Any]) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "role_label": LABELS[self.role],
            "mode": self.mode.value,
            "mode_label": LABELS[self.mode],
            "goal": self.goal,
            "next_action": self.next_action(),
            "executed": self.executed,
            "deferred": self.deferred,
            "constraints": [c.to_dict() for c in self.constraints],
            "budget": self.budget.to_dict() if self.budget else {},
            "insights": [i.to_dict() for i in insights],
            "next_review_at": self.next_review_at.isoformat() if self.next_review_at else None,
        }


class Coordinator:
    def __init__(self, view: CoordinationView) -> None:
        self.view = view
        self.budget = Budget(view.ctx)

    def score(self, proposals: list[Proposal], mode: Role) -> list[Proposal]:
        weights = WEIGHTS[mode]
        for proposal in proposals:
            proposal.priority = weights.score(proposal.factors)

        return sorted(proposals, key=lambda p: (-p.priority, p.deadline or datetime.max))

    async def run(
        self,
        proposals: list[Proposal],
        constraints: list[Constraint],
        reservations: list[Reservation],
        execute: Execute,
    ) -> Decision:
        view = self.view
        decision = Decision(role=view.base_role, mode=view.role, goal=GOALS[view.role], constraints=constraints, budget=self.budget)

        for reservation in sorted(reservations, key=lambda r: Budget.KINDS.index(r.kind) if r.kind in Budget.KINDS else 9):
            self.budget.reserve(reservation)

        chosen: set[str] = set()
        failed: set[str] = set()
        slots = view.free_slots
        done = 0

        for proposal in self.score(self._unique(proposals), view.role):
            why = self._blocked(proposal, constraints, chosen, failed, slots, done)
            if not why and not self.view.dry_run:
                learned = await self.view.lessons.blocked(proposal.action, proposal.arguments)
                why = learned.replace("RECUSADO: ", "") if learned else None

            if why:
                decision.deferred.append(self._entry(proposal, why=why))
                continue

            ok, text = await execute(proposal)
            decision.executed.append(self._entry(proposal, ok=ok, result=text))

            if ok:
                chosen.add(proposal.key)
                done += 1
                if proposal.purpose:
                    self.budget.release(proposal.purpose)
                if proposal.action in BUILD_ACTIONS:
                    slots -= 1
            else:
                failed.add(proposal.key)

        decision.next_review_at = self._next_review(decision)
        return decision

    @staticmethod
    def _unique(proposals: list[Proposal]) -> list[Proposal]:
        best: dict[str, Proposal] = {}
        for proposal in proposals:
            current = best.get(proposal.key)
            if current is None or proposal.factors.impact + proposal.factors.urgency > current.factors.impact + current.factors.urgency:
                best[proposal.key] = proposal

        return list(best.values())

    def _blocked(
        self, proposal: Proposal, constraints: list[Constraint], chosen: set[str], failed: set[str], slots: int, done: int
    ) -> str | None:
        for constraint in constraints:
            if constraint.violated_by(proposal):
                return f"vetado: {constraint.reason}"

        if proposal.action in self.view.config.approval_actions:
            return "aguardando aprovação do jogador"

        if proposal.key in self.view.recent:
            return "feito há pouco; aguardando confirmação do jogo"

        missing = [d for d in proposal.dependencies if d not in chosen and d not in self.view.satisfied]
        if missing:
            return f"depende de {', '.join(missing)}"

        if proposal.action in BUILD_ACTIONS and slots <= 0:
            return "fila de construção cheia"

        if done >= MAX_ACTIONS:
            return "limite de ações por rodada"

        if proposal.troops and not self.budget.troops_available(proposal.troops, proposal.purpose):
            return "tropas comprometidas ou fora de casa"

        if proposal.cost and not self.budget.affordable(proposal.cost, proposal.purpose, proposal.action):
            short = self.budget.shortfall(proposal.cost, proposal.purpose, proposal.action)
            stock = self.budget.stock()
            reserved = [r.purpose for r in self.budget.reservations if r.purpose != proposal.purpose and r.cost and r.covers(proposal.action)]
            if all(stock[k] >= proposal.cost.get(k, 0) for k in short) and reserved:
                return f"consumiria recursos reservados para {', '.join(reserved)}"

            hours = self.view.estimator.hours_to_afford(proposal.cost, self.budget.free(proposal.purpose, proposal.action))
            eta = f", disponível em ~{hours:.1f}h" if hours != float("inf") else ""
            if proposal.cost.get("pop", 0) > self.view.ctx.pop_free:
                return "falta população (fazenda)"

            return "faltam " + ", ".join(f"{v} {k}" for k, v in short.items()) + eta

        return None

    def _entry(self, proposal: Proposal, **extra: Any) -> dict[str, Any]:
        entry = proposal.to_dict()
        entry.update(extra)
        if "why" in extra and proposal.cost:
            hours = self.view.estimator.hours_to_afford(proposal.cost, self.budget.free(proposal.purpose, proposal.action))
            entry["ready_in_hours"] = None if hours == float("inf") else round(hours, 2)

        return entry

    def _next_review(self, decision: Decision) -> datetime:
        floor = now() + timedelta(minutes=self.view.config.interval_minutes)
        estimator = self.view.estimator
        events = [now() + timedelta(hours=e["ready_in_hours"]) for e in decision.deferred if e.get("ready_in_hours")]

        for hours in (estimator.queue_hours(), estimator.hours_to_impact(), estimator.storage_hours()):
            if hours and hours != float("inf"):
                events.append(now() + timedelta(hours=hours))

        return max(floor, min(events)) if events else floor
