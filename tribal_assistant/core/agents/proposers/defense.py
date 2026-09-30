"""Defense: incoming attacks become vetoes, reservations, a hold-or-dodge answer and the preparation before protection ends."""

from datetime import timedelta

from tribal_assistant.core.agents.coordination.budget import Reservation
from tribal_assistant.core.agents.coordination.constraints import Constraint
from tribal_assistant.core.agents.coordination.incoming import (
    Assessment,
    DodgePlanner,
    IncomingWatch,
)
from tribal_assistant.core.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.roles import RoleSelector
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.coordination.threat import ThreatScan
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import Knobs, knob, knob_int, tuning
from tribal_assistant.core.agents.proposers.base import Proposer, clamp
from tribal_assistant.core.errors import DomainError
from tribal_assistant.core.services.world import WorldService

DEFENDERS = ("spear", "sword", "archer", "heavy")
SPEND_BLOCKED = ("train_knight", "accept_market_offer", "use_item")
HIDE_CAPACITY = (0, 150, 200, 267, 356, 474, 632, 843, 1125, 1500, 2000)


class DefenseProposer(Proposer):
    key = "defense"
    title = "Defesa"
    observes = "ataques recebidos, origem, unidade mais lenta, tropas e tempo até o impacto"
    delivers = "alertas, vetos temporários, esquiva ou defesa e a preparação antes do fim da proteção"

    def __init__(self) -> None:
        self._assessed: tuple[int, Assessment | None] | None = None

    def _threat(self, view: CoordinationView) -> float | None:
        return view.estimator.hours_to_impact()

    async def assess(self, view: CoordinationView) -> Assessment | None:
        key = id(view)
        if self._assessed is None or self._assessed[0] != key:
            watch = IncomingWatch(view.session)
            attacks = [a for a in await watch.attacks(view.ctx) if not a.same_tribe]
            planner = DodgePlanner(view.session, await watch.clock(), tuning(view))
            decision = planner.decide(view.ctx, attacks[0]) if attacks else None
            if decision is not None and decision.action == "dodge":
                decision = await self._dodge_target(view, planner, decision)

            self._assessed = (key, decision)

        return self._assessed[1]

    async def _dodge_target(self, view: CoordinationView, planner: DodgePlanner, decision: Assessment) -> Assessment:
        try:
            rows = await WorldService(view.session).nearby(view.ctx.id, "barbarian", knob_int(view, "dodge.radius"), 400)
        except DomainError:
            rows = []

        found = planner.target(view.ctx, decision.attack, decision.troops, [(r.coords, r.distance) for r in rows])
        if found is None:
            decision.action = "hold"
            decision.reason += "; nenhuma bárbara no raio longe o bastante para esquivar"
            return decision

        decision.target, decision.travel_minutes = found
        return decision

    async def constraints(self, view: CoordinationView) -> list[Constraint]:
        hours = self._threat(view)
        if hours is None:
            return []

        decision = await self.assess(view)
        until = now() + timedelta(hours=hours + knob(view, "defense.hold_margin_hours"))
        view.note(Insight("threat", self._describe(hours, decision), Certainty.ESTIMATE if decision else Certainty.HYPOTHESIS, now(), 0.6 if decision else 0.5, hours, self.key))
        if decision is not None and decision.action == "dodge":
            return [Constraint("block_actions", "esquiva: gastar recursos e tirar as tropas antes do impacto", self.key, until, (*SPEND_BLOCKED, "send_scavenge"))]

        return [
            Constraint("hold_troops", "ataque chegando: tropas ficam em casa até o impacto", self.key, until),
            Constraint("block_actions", "ataque chegando: não gastar com paladino, mercado ou itens", self.key, until, SPEND_BLOCKED),
        ]

    def _describe(self, hours: float, decision: Assessment | None) -> str:
        if decision is None:
            return f"ataque chega em {hours:.1f}h; tamanho desconhecido"

        attack = decision.attack
        origin = f"de {attack.player or '?'} ({attack.origin})" if attack.origin else "origem desconhecida"
        return f"ataque {attack.tag} {origin} chega em {hours:.1f}h: {decision.action} ({decision.reason})"

    async def reservations(self, view: CoordinationView) -> list[Reservation]:
        hours = self._threat(view)
        if hours is None:
            return []

        decision = await self.assess(view)
        dodging = decision is not None and decision.action == "dodge"
        home = {} if dodging else {u.name: u.home for u in view.ctx.village.units if u.name in DEFENDERS and u.home}
        wall = view.build_cost("wall")
        return [
            Reservation(
                "defense",
                "defense",
                f"resposta ao ataque em {hours:.1f}h: muralha" + ("" if dodging else " e defensores"),
                {k: v for k, v in wall.items() if k != "pop"},
                home,
            )
        ]

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        hours = self._threat(view)
        if hours is None:
            return await self._prepare(view)

        decision = await self.assess(view)
        urgency = clamp(1 - hours / knob(view, "defense.urgency_horizon_hours"))
        deadline = now() + timedelta(hours=hours)
        items = []

        if decision is not None and decision.action == "dodge" and decision.target:
            items.append(self._dodge(decision, urgency, deadline))

        if not view.guard.check_upgrade(view.ctx, "wall"):
            items.append(
                Proposal(
                    self.key,
                    "upgrade_building",
                    {"building": "wall", "reason": "ataque chegando: muralha"},
                    f"ataque em {hours:.1f}h",
                    "muralha multiplica a defesa e gasta recursos que seriam saqueados",
                    cost=view.build_cost("wall"),
                    factors=Factors(urgency=urgency, impact=0.5, risk_avoided=0.9),
                    horizon=Horizon.IMMEDIATE,
                    deadline=deadline,
                    confidence=0.9,
                    purpose="defense",
                    key="upgrade_building:wall",
                )
            )

        if decision is not None and decision.action == "dodge":
            return items

        for unit in ("spear", "sword"):
            plan = view.guard.plan_recruit(view.ctx, unit, knob_int(view, "defense.batch"))
            if plan.refusal:
                continue

            items.append(
                Proposal(
                    self.key,
                    "recruit_units",
                    {"unit": unit, "count": plan.count, "reason": "ataque chegando: defensores"},
                    f"ataque em {hours:.1f}h",
                    "mais defesa em casa",
                    cost=view.unit_cost(unit, plan.count),
                    factors=Factors(urgency=urgency, impact=0.4, risk_avoided=0.8),
                    horizon=Horizon.IMMEDIATE,
                    deadline=deadline,
                    confidence=0.7,
                    purpose="defense",
                    risks=["tropas podem não ficar prontas antes do impacto"],
                )
            )
            break

        return items

    def _dodge(self, decision: Assessment, urgency: float, deadline) -> Proposal:
        attack = decision.attack
        return Proposal(
            self.key,
            "send_farm_attack",
            {"target": decision.target, "units": dict(decision.troops), "reason": "esquiva: tropas fora no impacto"},
            f"ataque {attack.tag} de {attack.origin or '?'} supera a defesa: {decision.reason}",
            f"tropas saqueiam {decision.target} e voltam em {2 * (decision.travel_minutes or 0):.0f} min, depois do impacto",
            troops=dict(decision.troops),
            factors=Factors(urgency=max(urgency, 0.6), impact=0.6, risk_avoided=0.95),
            horizon=Horizon.IMMEDIATE,
            deadline=deadline,
            confidence=0.7,
            purpose="defense",
            key=f"dodge:{decision.target}",
            risks=["estimativa do ataque pode estar errada", "a bárbara pode ter tropas"],
        )

    async def _prepare(self, view: CoordinationView) -> list[Proposal]:
        """Before beginner protection ends (from 72h out) or in defense role: wall, hiding place, defenders, spies, watchtower."""

        ctx = view.ctx
        protection = RoleSelector.protection_hours(ctx)
        prepare = knob(view, "defense.prepare_hours")
        wall, spears, swords = (knob_int(view, f"defense.{name}_target") for name in ("wall", "spear", "sword"))
        ending = protection is not None and 0 < protection <= prepare
        defense_role = view.role == Role.DEFENSE
        if not ending and not defense_role:
            return []

        why = f"proteção de iniciante acaba em {protection:.0f}h" if ending else "papel defesa"
        urgency = clamp(1 - (protection or prepare / 2) / prepare) if ending else 0.4
        deadline = now() + timedelta(hours=protection) if ending else None
        view.note(Insight("protection", f"{why}: muralha {wall}, {spears} lanceiros e {swords} espadachins", Certainty.FACT, now(), 1.0, protection, self.key))

        hide = await self.hide_target(view)
        targets = [("wall", wall, 0.6, "muralha multiplica a defesa"), ("hide", hide, 0.4, "esconderijo protege recursos do saque")]
        if defense_role:
            targets.append(("watchtower", knob_int(view, "defense.watchtower_target"), 0.3, "torre de vigia mostra ataques chegando"))

        items = [p for p in (self._building(view, *t, why, urgency, deadline) for t in targets) if p]
        for unit, count in self.troop_goals(ctx, tuning(view)).items():
            proposal = self._recruit(view, unit, count, why, urgency, deadline)
            if proposal:
                items.append(proposal)

        return items

    def _building(self, view: CoordinationView, building: str, target: int, impact: float, benefit: str, why: str, urgency: float, deadline) -> Proposal | None:
        ctx = view.ctx
        current = ctx.building(building)
        if current is None or current.level >= target or current.blocker == "requisitos não atendidos":
            return None

        refusal = view.guard.check_upgrade(ctx, building) or ""
        if refusal and "recurso" not in refusal and "população" not in refusal:
            return None

        return Proposal(
            self.key,
            "upgrade_building",
            {"building": building, "reason": f"{why}: {building} {target}"},
            why,
            benefit,
            cost=view.build_cost(building),
            factors=Factors(urgency=urgency, impact=impact, risk_avoided=0.7),
            horizon=Horizon.TACTICAL,
            deadline=deadline,
            confidence=0.85,
            key=f"upgrade_building:{building}",
        )

    def troop_goals(self, ctx, knobs: Knobs | None = None) -> dict[str, int]:
        """Missing defenders: spears and swords first, archers matching swords 1:1 after, a few spies at home."""
        knobs = knobs or tuning(ctx)
        have = {name: (ctx.unit(name).total if ctx.unit(name) else 0) for name in ("spear", "sword", "archer", "spy")}
        goals = {
            "spear": knobs.int("defense.spear_target") - have["spear"],
            "sword": knobs.int("defense.sword_target") - have["sword"],
            "spy": knobs.int("defense.spy_home") - have["spy"],
        }
        if goals["spear"] <= 0 and goals["sword"] <= 0:
            goals["archer"] = have["sword"] - have["archer"]

        return {u: min(knobs.int("defense.batch"), n) for u, n in goals.items() if n > 0 and ctx.unit(u) and ctx.unit(u).available}

    def _recruit(self, view: CoordinationView, unit: str, count: int, why: str, urgency: float, deadline) -> Proposal | None:
        plan = view.guard.plan_recruit(view.ctx, unit, count)
        if plan.refusal:
            return None

        benefit = {
            "spear": "defesa contra cavalaria",
            "sword": "defesa contra infantaria",
            "archer": "com espadachins 1:1, a melhor defesa mista",
            "spy": "só espiões matam espiões: manter alguns em casa",
        }[unit]
        return Proposal(
            self.key,
            "recruit_units",
            {"unit": unit, "count": plan.count, "reason": f"{why}: {unit}"},
            why,
            benefit,
            cost=view.unit_cost(unit, plan.count),
            factors=Factors(urgency=urgency, impact=0.45 if unit != "spy" else 0.25, risk_avoided=0.6),
            horizon=Horizon.TACTICAL,
            deadline=deadline,
            confidence=0.85,
        )

    async def hide_target(self, view: CoordinationView) -> int:
        """Hiding place sized by risk: bigger with players close by, biggest with strong ones."""
        scan = ThreatScan(view.session, tuning(view))
        try:
            threats = await scan.near(view.ctx)
        except (ValueError, DomainError):
            threats = []

        dangerous = scan.dangerous(threats, view.ctx.village.points)
        return self.hide_level(len(threats), len(dangerous), view.ctx.village.storage or 0, tuning(view))

    @staticmethod
    def hide_level(neighbours: int, dangerous: int, storage: int, knobs: Knobs | None = None) -> int:
        knobs = knobs or Knobs()
        level = knobs.int("defense.hide_level_danger" if dangerous else "defense.hide_level_near" if neighbours else "defense.hide_level_calm")
        want = storage * knobs.get("defense.hide_share_danger" if dangerous else "defense.hide_share_near" if neighbours else "defense.hide_share_calm")
        while level < 10 and HIDE_CAPACITY[level] < want:
            level += 1

        return level
