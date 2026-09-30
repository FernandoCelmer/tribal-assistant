"""Turns proposals into an executed plan: role and mode, reservations, vetoes, scores, deferrals."""

import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from typing import Any

from tribal_assistant.core.agents.coordination.budget import Budget, Reservation
from tribal_assistant.core.agents.coordination.constraints import Constraint
from tribal_assistant.core.agents.coordination.insight import now
from tribal_assistant.core.agents.coordination.live import FlowFeed
from tribal_assistant.core.agents.coordination.proposal import Proposal
from tribal_assistant.core.agents.coordination.strategy import GOALS, LABELS, Role, Weights
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import knob, knob_int, tuning

Execute = Callable[[Proposal], Awaitable[tuple[bool, str]]]
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
    exploration: dict[str, Any] | None = None
    learned: dict[str, Any] = field(default_factory=dict)

    def next_action(self) -> dict[str, Any] | None:
        done = [e for e in self.executed if e["ok"]]
        if done:
            return done[0]

        return self.deferred[0] if self.deferred else None

    def summary(self) -> str:
        ok = [e["title"] for e in self.executed if e["ok"]]
        parts = [f"modo {LABELS[self.mode]}"]
        parts.append(f"feito: {', '.join(ok)}" if ok else "nada executado")
        if self.exploration:
            parts.append(self.exploration["reason"])
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
            "exploration": self.exploration,
            "learned": self.learned,
        }


class Coordinator:
    def __init__(self, view: CoordinationView, rng: random.Random | None = None) -> None:
        self.view = view
        self.budget = Budget(view.ctx)
        self.rng = rng or random.Random()

    def weights(self, mode: Role) -> Weights:
        knobs = tuning(self.view)
        return Weights(**{item.name: knobs.get(f"weight.{mode.value}.{item.name}") for item in fields(Weights)})

    def bonus(self, source: str) -> float:
        name = f"bonus.{source}"
        knobs = tuning(self.view)
        return knobs.get(name) if name in knobs.SPECS else 1.0

    def score(self, proposals: list[Proposal], mode: Role) -> list[Proposal]:
        weights = self.weights(mode)
        for proposal in proposals:
            proposal.bonus = self.bonus(proposal.source)
            proposal.priority = round(weights.score(proposal.factors) * proposal.bonus, 1)

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

        ordered = self.score(self._unique(proposals), view.role)
        decision.exploration = await self._explore(ordered, constraints)
        feed = FlowFeed(view.ctx)
        feed.plan(ordered)
        decision.learned = {
            "bonus": {source: round(self.bonus(source), 2) for source in sorted({p.source for p in ordered})},
            "explore_rate": round(knob(view, "coordinator.explore_rate"), 3),
        }

        for proposal in ordered:
            why = self._blocked(proposal, constraints, chosen, failed, slots, done) or await self._learned(proposal)

            if why:
                decision.deferred.append(self._entry(proposal, why=why))
                feed.deferred(proposal, why)
                continue

            feed.running(proposal)
            ok, text = await execute(proposal)
            feed.result(proposal, ok, text)
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

    async def _learned(self, proposal: Proposal) -> str | None:
        if self.view.dry_run:
            return None
        learned = await self.view.lessons.blocked(proposal.action, proposal.arguments, tuning(self.view))
        return learned.replace("RECUSADO: ", "") if learned else None

    async def _explore(self, ordered: list[Proposal], constraints: list[Constraint]) -> dict[str, Any] | None:
        """Now and then promote a viable proposal that would not come first; vetoes, reserves and limits still apply."""
        view = self.view
        rate = knob(view, "coordinator.explore_rate")
        if view.dry_run or view.role == Role.EMERGENCY or self.rng.random() >= rate:
            return None

        viable = []
        for proposal in ordered:
            if proposal.priority > 0 and not self._blocked(proposal, constraints, set(), set(), view.free_slots, 0) and not await self._learned(proposal):
                viable.append(proposal)
        if len(viable) < 2:
            return None

        first, pick = viable[0], self.rng.choice(viable[1:])
        ordered.remove(pick)
        ordered.insert(0, pick)
        pick.explored = True
        if "reason" in pick.arguments:
            pick.arguments["reason"] = f"exploração: {pick.arguments['reason']}"[:60]
        return {
            "key": pick.key,
            "title": pick.title(),
            "source": pick.source,
            "priority": pick.priority,
            "instead_of": first.title(),
            "instead_of_priority": first.priority,
            "rate": round(rate, 3),
            "reason": f"exploração: {pick.title()} antes de {first.title()}",
        }

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

        if proposal.key in self.view.recent:
            return "feito há pouco; aguardando confirmação do jogo"

        missing = [d for d in proposal.dependencies if d not in chosen and d not in self.view.satisfied]
        if missing:
            return f"depende de {', '.join(missing)}"

        if proposal.action in BUILD_ACTIONS and slots <= 0:
            return "fila de construção cheia"

        if done >= knob_int(self.view, "coordinator.max_actions"):
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
        """The first moment something changes (troops home, queue free, cost affordable), never later than the interval."""
        ceiling = now() + timedelta(minutes=self.view.config.interval_minutes)
        soonest = now() + timedelta(minutes=knob(self.view, "coordinator.min_review_minutes"))
        estimator = self.view.estimator
        events = [now() + timedelta(hours=e["ready_in_hours"]) for e in decision.deferred if e.get("ready_in_hours")]

        for hours in (estimator.queue_hours(), estimator.hours_to_impact(), estimator.storage_hours(), estimator.troops_back_hours()):
            if hours and hours != float("inf"):
                events.append(now() + timedelta(hours=hours))

        return max(soonest, min([ceiling, *events]))
