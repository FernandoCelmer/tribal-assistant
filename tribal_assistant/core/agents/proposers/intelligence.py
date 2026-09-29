"""Intelligence: consolidates reports, targets and neighbours into labelled insights and missing data."""

import json

from tribal_assistant.core.agents.challenges import ChallengePlan
from tribal_assistant.core.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.core.agents.coordination.proposal import Proposal
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import knob
from tribal_assistant.core.agents.proposers.base import Proposer


class IntelligenceProposer(Proposer):
    key = "intelligence"
    title = "Inteligência"
    observes = "relatórios, histórico dos vizinhos e desafios do jogo"
    delivers = "informações consolidadas e dados que faltam"

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        repo = view.lessons.repo
        stale_hours = knob(view, "intel.stale_hours")
        targets = await repo.list("target", limit=50)
        stale = []

        for row in targets:
            data = json.loads(row.data or "{}")
            age = (now() - row.last_seen).total_seconds() / 3600
            if age > stale_hours:
                stale.append(row.title.replace("alvo ", ""))

            if data.get("last_result") == "green" and data.get("last_haul", 0) and data.get("avg_haul", 0) >= data.get("last_haul", 0) * 0.9:
                view.note(
                    Insight(
                        row.key,
                        f"{row.title} parece sem defesa e com saque constante ({data.get('avg_haul')} por ataque)",
                        Certainty.HYPOTHESIS,
                        row.last_seen,
                        0.7,
                        data,
                        self.key,
                    )
                )

        if stale:
            view.note(Insight("stale_targets", f"relatórios velhos (>{stale_hours:.0f}h): {', '.join(stale[:5])}", Certainty.FACT, now(), 1.0, stale, self.key))

        tribes = await repo.list("tribe", limit=1)
        if tribes:
            first = tribes[0].text.splitlines()[:2]
            view.note(Insight("tribes", "vizinhança: " + " | ".join(first), Certainty.FACT, tribes[0].last_seen, 1.0, None, self.key))

        challenges = await repo.get("challenges")
        if challenges:
            close = ChallengePlan.closest(json.loads(challenges.data or "{}").get("items", []), limit=3)
            if close:
                text = "desafios mais perto: " + " | ".join(f"{c['name']} {c['current']}/{c['target']} ({c['how']})" for c in close)
                view.note(Insight("challenges", text, Certainty.FACT, challenges.last_seen, 1.0, close, self.key))

        if not targets:
            view.note(Insight("no_reports", "nenhum relatório de saque ainda: alvos são desconhecidos", Certainty.FACT, now(), 1.0, None, self.key))

        return []
