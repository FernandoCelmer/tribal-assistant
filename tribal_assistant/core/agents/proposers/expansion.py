"""Expansion: tracks the path to a nobleman and, in expansion role, reserves resources for it."""

import json
import math

from sqlalchemy import select

from tribal_assistant.core.agents.coordination.budget import Reservation
from tribal_assistant.core.agents.coordination.insight import Certainty, Insight, now
from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import knob, knob_int
from tribal_assistant.core.agents.noble import ACADEMY_PATH, Candidate, NobleReadiness, NobleTarget
from tribal_assistant.core.agents.proposers.base import Proposer
from tribal_assistant.core.game.world_config import WorldConfig
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.models.world import WorldVillage
from tribal_assistant.core.repositories.world import WorldRepository

NOBLE_PATH = (*ACADEMY_PATH, ("snob", 1))


class ExpansionProposer(Proposer):
    key = "expansion"
    title = "Expansão"
    observes = "capacidade econômica, tropas, caminho da academia e sistema de nobres do mundo"
    delivers = "plano e reserva para conquistar outra aldeia"

    def progress(self, view: CoordinationView) -> float:
        levels = view.ctx.levels
        return sum(min(1.0, levels.get(b, 0) / lvl) for b, lvl in NOBLE_PATH) / len(NOBLE_PATH)

    async def world(self, view: CoordinationView) -> WorldConfig:
        repo = WorldRepository(view.session)
        return WorldConfig.from_settings(await repo.setting("config"), await repo.setting("units"))

    async def ordinal(self, view: CoordinationView) -> int:
        own = (await view.session.execute(select(Village.id).where(Village.is_own.is_(True)))).scalars().all()
        snob = view.ctx.unit("snob")
        return max(1, len(own)) + (snob.total if snob else 0)

    async def noble_cost(self, view: CoordinationView) -> dict[str, int]:
        return (await self.world(view)).noble_cost(await self.ordinal(view))

    async def reservations(self, view: CoordinationView) -> list[Reservation]:
        if view.role != Role.EXPANSION or not NobleReadiness.ready(view.ctx):
            return []

        cost = await self.noble_cost(view)
        fraction = knob(view, "expansion.reserve_share")
        share = {r: min(int(view.ctx.stock.get(r, 0) * fraction), cost[r]) for r in ("wood", "clay", "iron")}
        return [Reservation("expansion", "strategic", f"{fraction:.0%} guardado para academia e nobre", share)]

    async def target(self, view: CoordinationView) -> Candidate | None:
        ox, oy = (int(n) for n in view.ctx.village.coords.split("|"))
        radius = knob_int(view, "expansion.target_radius")
        rows = (
            await view.session.execute(
                select(WorldVillage)
                .where(WorldVillage.player_id == 0)
                .where(WorldVillage.x.between(ox - radius, ox + radius))
                .where(WorldVillage.y.between(oy - radius, oy + radius))
            )
        ).scalars().all()

        known = set()
        for lesson in await view.lessons.repo.list("target", limit=200):
            if json.loads(lesson.data or "{}").get("last_result") == "green":
                known.add(lesson.key.removeprefix("target:"))

        own = set((await view.session.execute(select(Village.coords).where(Village.is_own.is_(True)))).scalars().all())
        candidates = [
            Candidate(f"{v.x}|{v.y}", v.points, round(math.hypot(v.x - ox, v.y - oy), 1), v.bonus_id, f"{v.x}|{v.y}" in known)
            for v in rows
            if f"{v.x}|{v.y}" not in own
        ]
        return NobleTarget.pick(candidates, radius)

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        progress = self.progress(view)
        view.note(Insight("noble_path", f"caminho do nobre: {progress:.0%}", Certainty.FACT, now(), 1.0, progress, self.key))

        if view.role != Role.EXPANSION or not view.free_slots:
            return []

        missing = NobleReadiness.missing(view.ctx)
        if missing:
            view.note(Insight("noble_gate", f"nobre espera: {', '.join(missing)}", Certainty.FACT, now(), 1.0, missing, self.key))

        world = await self.world(view)
        cost = world.noble_cost(await self.ordinal(view))
        target = await self.target(view)
        where = f"alvo {target.coords} ({target.points} pts)" if target else "sem alvo bárbaro próximo"
        view.note(
            Insight(
                "noble_plan",
                f"nobre por {world.noble_system}: {cost['wood']}/{cost['clay']}/{cost['iron']}; {where}",
                Certainty.ESTIMATE,
                now(),
                0.8,
                cost,
                self.key,
                {"target": target.coords if target else None},
            )
        )

        levels = view.ctx.levels
        for building, target_level in NOBLE_PATH:
            if building == "snob" and missing:
                return []

            if levels.get(building, 0) < target_level and not view.guard.check_upgrade(view.ctx, building):
                return [
                    Proposal(
                        self.key,
                        "upgrade_building",
                        {"building": building, "reason": "caminho do nobre"},
                        f"{building} {target_level} é requisito da academia",
                        "aproxima a segunda aldeia",
                        cost=view.build_cost(building),
                        factors=Factors(urgency=0.1, impact=0.8, opportunity=0.3),
                        horizon=Horizon.STRATEGIC,
                        confidence=1.0,
                        purpose="expansion",
                        key=f"upgrade_building:{building}",
                    )
                ]

        return []
