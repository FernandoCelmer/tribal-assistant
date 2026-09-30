"""Conquest: a noble at home goes after the chosen barbarian, scouted and cleared first."""

from tribal_assistant.core.agents.conquest import ConquestBook, ConquestPlanner, ConquestStep
from tribal_assistant.core.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import knob_int, tuning
from tribal_assistant.core.agents.noble import Candidate
from tribal_assistant.core.agents.proposers.base import Proposer
from tribal_assistant.core.agents.proposers.expansion import ExpansionProposer


class ConquestProposer(Proposer):
    key = "conquest"
    title = "Conquista"
    observes = "nobres em casa, bárbara alvo, espionagem, limpeza e lealdade estimada"
    delivers = "espionagem, limpeza e nobres (em trem quando há vários) contra uma bárbara"

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        snob = ctx.unit("snob")
        if snob is None or snob.home <= 0:
            return []

        target = await ExpansionProposer().target(view)
        if target is None:
            view.note(Insight("conquest", "nobre em casa sem bárbara no raio de conquista", Certainty.FACT, now(), 1.0, None, self.key))
            return []

        book = ConquestBook(view.session)
        home = {u.name: u.home for u in ctx.village.units}
        travelling = any(c.get("direction") == "out" and c.get("coords") == target.coords for c in ctx.commands)
        step = ConquestPlanner.step(await view.lessons.target(target.coords), await book.state(target.coords), home, await book.per_hour(), tuning(view), travelling)
        view.note(Insight("conquest", f"conquista de {target.coords}: {step.why}", Certainty.ESTIMATE, now(), 0.8, {"step": step.kind, "loyalty": round(step.loyalty)}, self.key))

        spies = knob_int(view, "spy.min_send")
        if step.kind == "scout" and home.get("spy", 0) >= spies:
            return [self._scout(target, spies)]

        if step.kind == "cleanup":
            return [self._cleanup(target, step)]

        if step.kind == "noble":
            return [self._noble(target, step)]

        return []

    def _scout(self, target: Candidate, spies: int) -> Proposal:
        return Proposal(
            self.key,
            "send_spy",
            {"target": target.coords, "count": spies, "reason": "espionar alvo do nobre"},
            f"alvo do nobre {target.coords} sem espionagem recente",
            "tropas e muralha antes da limpeza",
            troops={"spy": spies},
            factors=Factors(urgency=0.5, impact=0.6, opportunity=0.6),
            horizon=Horizon.IMMEDIATE,
            confidence=0.95,
            key=f"send_spy:{target.coords}",
        )

    def _cleanup(self, target: Candidate, step: ConquestStep) -> Proposal:
        return Proposal(
            self.key,
            "send_farm_attack",
            {"target": target.coords, "units": step.squad, "reason": "limpeza antes do nobre"},
            step.why,
            "bárbara sem defensores para o nobre",
            troops=step.squad,
            factors=Factors(urgency=0.6, impact=0.8, opportunity=0.6),
            horizon=Horizon.IMMEDIATE,
            confidence=0.9,
            risks=["perdas se a bárbara cresceu desde a espionagem"],
            key=f"send_farm_attack:{target.coords}",
        )

    def _noble(self, target: Candidate, step: ConquestStep) -> Proposal:
        troops = {u: n * step.nobles for u, n in step.escort.items()} | {"snob": step.nobles}
        return Proposal(
            self.key,
            "send_noble",
            {"target": target.coords, "nobles": step.nobles, "escort": step.escort, "reason": "conquista de bárbara"},
            step.why,
            f"lealdade de {target.coords} cai ~{step.loyalty:.0f} → conquista",
            troops=troops,
            factors=Factors(urgency=0.8, impact=1.0, opportunity=0.8),
            horizon=Horizon.IMMEDIATE,
            confidence=0.9,
            risks=["nobre morre se a bárbara tiver defensores"],
            key=f"send_noble:{target.coords}",
        )
