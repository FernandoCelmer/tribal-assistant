"""Attack: barbarian raids ranked by what the reports taught, and idle troops sent scavenging."""

import json

from tribal_assistant.agents.coordination.constraints import Constraint
from tribal_assistant.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.agents.coordination.strategy import Role
from tribal_assistant.agents.coordination.view import CoordinationView
from tribal_assistant.agents.guardrails import SCAVENGE_MIN_POP
from tribal_assistant.agents.knowledge import UNITS
from tribal_assistant.agents.proposers.base import Proposer, clamp

SQUADS = ({"light": 5}, {"spear": 10}, {"axe": 10}, {"spear": 5})
MAX_RAIDS = 3
SCAVENGERS = ("spear", "sword", "axe", "archer", "light", "marcher", "heavy")
MIN_CONFIDENCE = 0.35


class AttackProposer(Proposer):
    key = "attack"
    title = "Ataque"
    observes = "alvos, relatórios, distâncias e tropas disponíveis"
    delivers = "propostas de saque com nível de confiança"

    async def constraints(self, view: CoordinationView) -> list[Constraint]:
        return [
            Constraint(
                "min_confidence",
                f"não atacar com confiança abaixo de {MIN_CONFIDENCE:.0%} (informação velha ou alvo que já custou tropas)",
                self.key,
                blocks=("send_farm_attack",),
                min_confidence=MIN_CONFIDENCE,
            )
        ]

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        items = await self._raids(view)
        scavenge = self._scavenge(view, reserved={u: n for p in items for u, n in p.troops.items()})
        if scavenge:
            items.append(scavenge)

        return items

    async def _raids(self, view: CoordinationView) -> list[Proposal]:
        listing = await view.read("list_barbarians")
        if not listing.ok or not listing.text.startswith("["):
            return []

        ctx = view.ctx
        home = {u.name: u.home for u in ctx.village.units}
        weight = 0.7 if view.role == Role.OFFENSIVE else 0.5
        items = []

        for target in json.loads(listing.text):
            if len(items) >= MAX_RAIDS:
                break

            if target.get("recently_attacked"):
                continue

            squad = next((s for s in SQUADS if all(home.get(u, 0) >= n for u, n in s.items())), None)
            if squad is None:
                break

            confidence, why = await self._confidence(view, target)
            carry = sum(UNITS[u].carry * n for u, n in squad.items() if u in UNITS)
            haul = target.get("avg_haul") or carry * 0.5
            for unit, count in squad.items():
                home[unit] -= count

            items.append(
                Proposal(
                    self.key,
                    "send_farm_attack",
                    {"target": target["coords"], "units": squad, "reason": "saque de bárbara próxima"},
                    f"bárbara a {target.get('distance')} campos; {why}",
                    f"~{int(haul)} recursos",
                    troops=squad,
                    factors=Factors(urgency=0.3, impact=weight, opportunity=clamp(haul / max(carry, 1))),
                    horizon=Horizon.IMMEDIATE,
                    confidence=confidence,
                    risks=["perdas se a bárbara tiver muralha ou tropas"],
                    key=f"send_farm_attack:{target['coords']}",
                )
            )

        return items

    @staticmethod
    async def _confidence(view: CoordinationView, target: dict) -> tuple[float, str]:
        row = await view.lessons.repo.get(f"target:{target['coords']}")
        if row is None:
            return 0.6, "sem relatório: alvo desconhecido"

        data = json.loads(row.data or "{}")
        insight = Insight(
            f"target:{target['coords']}",
            row.text,
            Certainty.HYPOTHESIS if data.get("last_result") != "green" else Certainty.ESTIMATE,
            row.last_seen,
            0.9 if data.get("last_result") == "green" else 0.55 if data.get("last_result") == "yellow" else 0.2,
            data,
            "relatórios",
        )
        view.note(insight)
        return max(0.3, insight.weight(half_life_hours=24)), f"último relatório {data.get('last_result', '?')} há {insight.age_hours():.0f}h"

    def _scavenge(self, view: CoordinationView, reserved: dict[str, int]) -> Proposal | None:
        ctx = view.ctx
        free = sorted(
            (o for o in ctx.village.scavenge if not o.is_locked and o.return_at is None), key=lambda o: o.option_id, reverse=True
        )
        if not free:
            return None

        units = {}
        for name in SCAVENGERS:
            unit = ctx.unit(name)
            count = (unit.home if unit else 0) - reserved.get(name, 0)
            if count > 0:
                units[name] = count

        pop = sum(UNITS[u].pop * n for u, n in units.items() if u in UNITS)
        if pop < SCAVENGE_MIN_POP:
            view.note(Insight("scavenge_pop", f"coleta parada: só {pop} de população em casa (mínimo {SCAVENGE_MIN_POP})", Certainty.FACT, now(), 1.0, pop, self.key))
            return None

        return Proposal(
            self.key,
            "send_scavenge",
            {"option_id": free[0].option_id, "units": units, "reason": "tropas ociosas coletando"},
            "tropas paradas em casa",
            f"coleta {free[0].option_id}",
            troops=units,
            factors=Factors(urgency=0.2, impact=0.35, opportunity=0.5),
            horizon=Horizon.IMMEDIATE,
            confidence=0.95,
            key="send_scavenge",
        )
