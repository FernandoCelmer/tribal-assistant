"""Attack: barbarian raids ranked by what the reports taught, and idle troops sent scavenging."""

import json
import statistics

from tribal_assistant.core.agents.coordination.constraints import Constraint
from tribal_assistant.core.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import Knobs, knob, knob_int, tuning
from tribal_assistant.core.agents.knowledge import UNITS
from tribal_assistant.core.agents.proposers.base import Proposer, clamp
from tribal_assistant.core.agents.proposers.farm import FarmChoice, FarmPlanner
from tribal_assistant.core.agents.proposers.raid import RaidPlan, RaidPlanner
from tribal_assistant.core.game.scraper.farm_assistant import TEMPLATES, FarmAssistantParser

SCAVENGERS = ("spear", "sword", "axe", "archer", "light", "marcher", "heavy")


class AttackProposer(Proposer):
    key = "attack"
    title = "Ataque"
    observes = "alvos, relatórios, distâncias e tropas disponíveis"
    delivers = "propostas de saque com nível de confiança"

    async def constraints(self, view: CoordinationView) -> list[Constraint]:
        least = knob(view, "raid.min_confidence")
        return [
            Constraint(
                "min_confidence",
                f"não atacar com confiança abaixo de {least:.0%} (informação velha ou alvo que já custou tropas)",
                self.key,
                blocks=("send_farm_attack", "send_farm_template"),
                min_confidence=least,
            )
        ]

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        items = await self._raids(view)
        viable = [p for p in items if p.confidence >= knob(view, "raid.min_confidence")]
        items += self._scavenge(view, reserved={u: n for p in viable for u, n in p.troops.items()})

        return items

    async def _raids(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        knobs = tuning(view)
        listing = await view.read("list_barbarians", {"limit": knobs.int("raid.listing")})
        if not listing.ok or not listing.text.startswith("["):
            return []

        targets = json.loads(listing.text)
        home = {u.name: u.home for u in ctx.village.units}
        light = ctx.unit("light")
        ram = ctx.unit("ram")
        has_ram = bool(ram and ram.total)
        budget = RaidPlanner.max_raids(light.total if light else 0, ctx.policy.max_attacks_per_hour, await view.guard.attacks_last_hour(ctx), knobs)
        median = statistics.median([int(t.get("points") or 0) for t in targets]) if targets else 0
        farm, setup = await self._farm_assistant(view, targets)
        intel = {t["coords"]: await view.lessons.target(t["coords"]) for t in targets}

        ranked = [RaidPlanner.plan(t, intel[t["coords"]], home, median, has_ram, knobs) for t in targets]
        order = {"probe": 0, "raid": 1, "skip": 2}
        ranked.sort(key=lambda p: (order[p.kind], -p.rate))
        by_coords = {t["coords"]: t for t in targets}

        weight = 0.7 if view.role == Role.OFFENSIVE else 0.5
        items: list[Proposal] = []
        probes = 0

        for first in ranked:
            if len(items) >= budget or first.kind == "skip":
                break

            target = by_coords[first.coords]
            plan = RaidPlanner.plan(target, intel[first.coords], home, median, has_ram, knobs)
            if plan.kind == "probe":
                if probes >= knobs.int("raid.max_probes") or await view.guard.spied_recently(plan.coords, ctx.policy.retarget_minutes):
                    continue

                probes += 1
                items.append(self._probe(plan, target))
            elif plan.kind == "raid":
                choice = self._farm_choice(farm, plan, target, intel[first.coords], home, knobs)
                items.append(await self._raid(view, plan, target, weight, choice))
                if choice is not None:
                    plan.squad = choice.squad
            else:
                continue

            for unit, count in plan.squad.items():
                home[unit] = home.get(unit, 0) - count

        return [setup, *items] if setup else items

    async def _farm_assistant(self, view: CoordinationView, targets: list[dict]) -> tuple[dict | None, Proposal | None]:
        """The assistant state when its templates are ready; otherwise a proposal to save them and the rally point this round."""
        outcome = await view.read("read_farm_assistant")
        state = outcome.data if outcome.ok else {}
        if not state.get("available"):
            return None, None

        knobs = tuning(view)
        full, seen = FarmPlanner.hauls(state.get("targets") or [])
        if seen:
            view.note(Insight("farm_hauls", f"assistente de saque: {full}/{seen} relatórios com carga cheia", Certainty.FACT, now(), 1.0, full / seen, self.key))

        barbarians = {t["coords"] for t in targets}
        walls = []
        for row in state.get("targets") or []:
            if row.get("coords") in barbarians:
                wall = (await view.lessons.target(row["coords"])).get("wall")
                walls.append(int(wall if wall is not None else row.get("wall") or 0))

        totals = {u.name: u.total for u in view.ctx.village.units}
        wanted = FarmPlanner.templates(totals, walls, knobs)
        if not wanted["a"]:
            return None, None

        current = {k: FarmAssistantParser.squad(state, k) for k in TEMPLATES}
        if FarmPlanner.drifted(current, wanted, knobs):
            return None, Proposal(
                self.key,
                "set_farm_templates",
                {**wanted, "reason": "modelos A e B no tamanho ideal"},
                f"modelos salvos {current}, ideal {wanted}",
                "saques pelo assistente com o grupo certo",
                factors=Factors(urgency=0.3, impact=0.4, opportunity=0.6),
                horizon=Horizon.IMMEDIATE,
                confidence=0.95,
            )

        return {"state": state, "templates": current}, None

    @staticmethod
    def _farm_choice(farm: dict | None, plan: RaidPlan, target: dict, data: dict, home: dict[str, int], knobs: Knobs) -> FarmChoice | None:
        if farm is None:
            return None

        row = FarmAssistantParser.target(farm["state"], plan.coords)
        if row is None or not row.get("village_id"):
            return None

        choice = FarmPlanner.choose({**row, "distance": target.get("distance") or row.get("distance")}, data, farm["templates"], home, knobs)
        if choice is not None:
            choice.target_id = int(row["village_id"])
        return choice

    def _probe(self, plan: RaidPlan, target: dict) -> Proposal:
        return Proposal(
            self.key,
            "send_spy",
            {"target": plan.coords, "count": plan.squad["spy"], "reason": "sondar bárbara antes do saque"},
            f"bárbara a {target.get('distance')} campos; {plan.why}",
            "muralha, recursos e tropas do alvo",
            troops=plan.squad,
            factors=Factors(urgency=0.3, impact=0.4, opportunity=0.6),
            horizon=Horizon.IMMEDIATE,
            confidence=0.9,
            risks=["perde o explorador se a bárbara tiver exploradores"],
            key=f"send_spy:{plan.coords}",
        )

    async def _raid(self, view: CoordinationView, plan: RaidPlan, target: dict, weight: float, choice: FarmChoice | None = None) -> Proposal:
        confidence, why = await self._confidence(view, target)
        if choice is not None:
            carry = self.carry(choice.squad)
            haul = min(plan.haul, float(carry))
            return Proposal(
                self.key,
                "send_farm_template",
                {"target": plan.coords, "target_id": choice.target_id, "template": choice.template, "units": choice.squad, "reason": "saque pelo assistente"},
                f"bárbara a {target.get('distance')} campos; {choice.why}; {why}",
                f"~{int(haul)} recursos",
                troops=choice.squad,
                factors=Factors(urgency=0.3, impact=weight, opportunity=clamp(haul / max(carry, 1))),
                horizon=Horizon.IMMEDIATE,
                confidence=confidence,
                risks=["perdas se a bárbara tiver muralha ou tropas"],
            )

        carry = self.carry(plan.squad)
        return Proposal(
            self.key,
            "send_farm_attack",
            {"target": plan.coords, "units": plan.squad, "reason": "saque de bárbara próxima"},
            f"bárbara a {target.get('distance')} campos; {plan.why}; {why}",
            f"~{int(plan.haul)} recursos ({int(plan.rate)}/h)",
            troops=plan.squad,
            factors=Factors(urgency=0.3, impact=weight, opportunity=clamp(plan.haul / max(carry, 1))),
            horizon=Horizon.IMMEDIATE,
            confidence=confidence,
            risks=["perdas se a bárbara tiver muralha ou tropas"],
            key=f"send_farm_attack:{plan.coords}",
        )

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
        return max(0.3, insight.weight(half_life_hours=knob(view, "raid.intel_half_life_hours"))), f"último relatório {data.get('last_result', '?')} há {insight.age_hours():.0f}h"

    @staticmethod
    def carry(squad: dict[str, int]) -> int:
        return RaidPlanner.carry(squad)

    @staticmethod
    def squad(home: dict[str, int], want: int) -> dict[str, int] | None:
        """Smallest group of raiders, fastest carriers first, that can take `want` resources."""
        return RaidPlanner.squad(home, want)

    @staticmethod
    def scavenge_seconds(haul: float) -> float:
        """Game formula for a scavenging run, before the world speed factor (the same for every tier)."""
        return (haul * haul * 100) ** 0.45 + 1800

    @classmethod
    def tier_sets(cls, carry: int, factors: dict[int, float]) -> list[tuple[int, ...]]:
        """Every combination of free tiers, best resources per minute first when all of them end together."""
        tiers = sorted(factors)
        sets = [tuple(t for i, t in enumerate(tiers) if mask >> i & 1) for mask in range(1, 1 << len(tiers))]

        def rate(chosen: tuple[int, ...]) -> float:
            haul = carry / sum(1 / factors[t] for t in chosen)
            return len(chosen) * haul / cls.scavenge_seconds(haul)

        return sorted(sets, key=rate, reverse=True)

    @classmethod
    def split(cls, units: dict[str, int], factors: dict[int, float], least: int | None = None) -> dict[int, dict[str, int]]:
        """Troops for the tiers that yield the most per minute, shared 1/loot factor so every run ends together; each part at least the world's minimum."""
        least = least if least is not None else Knobs().int("scavenge.min_pop")
        def pop(part: dict[str, int]) -> int:
            return sum(UNITS[u].pop * n for u, n in part.items() if u in UNITS)

        carry = sum(UNITS[u].carry * n for u, n in units.items() if u in UNITS)
        for chosen in cls.tier_sets(carry, factors):
            weights = {t: 1 / factors[t] for t in chosen}
            total = sum(weights.values())
            parts = {t: {u: int(n * weights[t] / total) for u, n in units.items()} for t in chosen}
            top = max(chosen)
            for unit, count in units.items():
                parts[top][unit] += count - sum(p[unit] for p in parts.values())

            parts = {t: {u: n for u, n in p.items() if n > 0} for t, p in parts.items()}
            if all(pop(p) >= least for p in parts.values()):
                return parts

        return {}

    def _scavenge(self, view: CoordinationView, reserved: dict[str, int]) -> list[Proposal]:
        ctx = view.ctx
        free = {o.option_id: o.loot_factor or 0.1 * o.option_id for o in ctx.village.scavenge if not o.is_locked and o.return_at is None}
        if not free:
            return []

        units = {}
        for name in SCAVENGERS:
            unit = ctx.unit(name)
            count = (unit.home if unit else 0) - reserved.get(name, 0)
            if count > 0:
                units[name] = count

        parts = self.split(units, free, knob_int(view, "scavenge.min_pop"))
        if not parts:
            pop = sum(UNITS[u].pop * n for u, n in units.items() if u in UNITS)
            view.note(Insight("scavenge_pop", f"coleta parada: só {pop} de população em casa (mínimo {knob_int(view, 'scavenge.min_pop')})", Certainty.FACT, now(), 1.0, pop, self.key))
            return []

        return [
            Proposal(
                self.key,
                "send_scavenge",
                {"option_id": option, "units": squad, "reason": "tropas ociosas coletando"},
                f"tropas paradas em casa; coleta {option} livre",
                f"coleta {option}",
                troops=squad,
                factors=Factors(urgency=0.2, impact=0.35, opportunity=0.5),
                horizon=Horizon.IMMEDIATE,
                confidence=0.95,
                key=f"send_scavenge:{option}",
            )
            for option, squad in parts.items()
        ]
