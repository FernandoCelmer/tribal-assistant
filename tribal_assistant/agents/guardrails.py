"""Hard limits every agent action passes through, whatever the model decided."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.agents.context import VillageContext
from tribal_assistant.agents.knowledge import UNITS, GameKnowledge
from tribal_assistant.models.farm_target import FarmTarget
from tribal_assistant.models.world import WorldVillage
from tribal_assistant.repositories.agents import AgentRepository
from tribal_assistant.schemas.agent_settings import AgentSettings

SCAVENGE_MIN_POP = 10


@dataclass(frozen=True)
class RecruitPlan:
    count: int
    refusal: str | None = None


class Guardrails:
    """Refuses actions that break the configured limits; returns the reason or None."""

    def __init__(self, session: AsyncSession, config: AgentSettings) -> None:
        self.session = session
        self.config = config
        self.repo = AgentRepository(session)

    def reserve(self, ctx: VillageContext) -> int:
        return int(ctx.village.storage * ctx.policy.resource_reserve)

    def check_upgrade(self, ctx: VillageContext, building: str) -> str | None:
        current = ctx.building(building)
        if current is None:
            return f"edifício {building!r} não existe nesta aldeia"

        if current.queued_level:
            return f"{building} já está na fila"

        if len(ctx.queue) >= ctx.policy.build_queue_slots:
            return "fila de construção cheia"

        if current.next_level is None or (current.max_level and current.level >= current.max_level):
            return f"{building} está no nível máximo"

        missing = GameKnowledge.missing_requirements(building, ctx.levels)
        if missing:
            return "requisitos faltando: " + ", ".join(f"{k} {v}" for k, v in missing.items())

        costs = {"wood": current.next_wood or 0, "clay": current.next_clay or 0, "iron": current.next_iron or 0}
        short = [k for k, v in costs.items() if v > ctx.stock[k]]
        if short:
            return "recursos insuficientes: " + ", ".join(short)

        if (current.next_pop or 0) > ctx.pop_free:
            return "população insuficiente; suba a fazenda"

        return None

    def check_unlock_scavenge(self, ctx: VillageContext, option_id: int) -> str | None:
        options = {o.option_id: o for o in ctx.village.scavenge}
        option = options.get(option_id)

        if option is None:
            return f"coleta {option_id} desconhecida; sincronize primeiro"

        if not option.is_locked:
            return f"coleta {option_id} já está desbloqueada"

        if option.unlock_at is not None:
            return f"coleta {option_id} já está sendo desbloqueada"

        previous = options.get(option_id - 1)
        if previous is not None and previous.is_locked and previous.unlock_at is None:
            return f"desbloqueie a coleta {option_id - 1} primeiro"

        return None

    def check_scavenge(self, ctx: VillageContext, option_id: int, units: dict[str, int]) -> str | None:
        option = next((o for o in ctx.village.scavenge if o.option_id == option_id), None)

        if option is None:
            return f"coleta {option_id} desconhecida; sincronize primeiro"

        if option.is_locked:
            return f"coleta {option_id} ainda bloqueada"

        if option.return_at is not None:
            return f"coleta {option_id} já está em andamento"

        if not units or sum(units.values()) <= 0:
            return "nenhuma tropa informada"

        for unit, count in units.items():
            current = ctx.unit(unit)
            if current is None or current.home < count:
                return f"só há {current.home if current else 0} {unit} em casa"

        pop = sum(UNITS[u].pop * n for u, n in units.items() if u in UNITS)
        if pop < SCAVENGE_MIN_POP:
            return f"coleta exige pelo menos {SCAVENGE_MIN_POP} de população; as tropas somam {pop}"

        if any(c["direction"] == "in" and c["kind"] in ("attack", "noble") for c in ctx.commands):
            return "ataque chegando; tropas ficam em casa"

        return None

    def plan_recruit(self, ctx: VillageContext, unit: str, count: int) -> RecruitPlan:
        current = ctx.unit(unit)
        if current is None:
            return RecruitPlan(0, f"unidade {unit!r} desconhecida")

        if not current.available:
            return RecruitPlan(0, current.blocker or f"{unit} indisponível")

        if count <= 0:
            return RecruitPlan(0, "quantidade deve ser positiva")

        reserve = self.reserve(ctx)
        limits = [count, current.max_recruit or count]
        storage = ctx.village.storage or 1
        near_full = any(value >= storage * 0.85 for value in ctx.stock.values())
        budget_share = max(ctx.policy.recruit_budget, 0.8) if near_full else ctx.policy.recruit_budget

        for key, cost in (("wood", current.cost_wood), ("clay", current.cost_clay), ("iron", current.cost_iron)):
            if cost:
                budget = max(0, ctx.stock[key] - reserve) * budget_share
                limits.append(int(budget // cost))

        if current.cost_pop:
            limits.append(ctx.pop_free // current.cost_pop)

        allowed = max(0, min(limits))
        if allowed == 0:
            return RecruitPlan(0, "sem orçamento: reserva de recursos ou população")

        return RecruitPlan(allowed)

    async def check_attack(self, ctx: VillageContext, target: str, units: dict[str, int]) -> str | None:
        try:
            tx, ty = (int(part) for part in target.split("|"))
            ox, oy = (int(part) for part in ctx.village.coords.split("|"))
        except ValueError:
            return f"coordenada inválida: {target!r}"

        if not units or sum(units.values()) <= 0:
            return "nenhuma tropa informada"

        for unit, count in units.items():
            current = ctx.unit(unit)
            if current is None or current.home < count:
                return f"só há {current.home if current else 0} {unit} em casa"

        distance = math.hypot(tx - ox, ty - oy)
        if distance > ctx.policy.attack_radius:
            return f"alvo a {distance:.1f} campos; limite {ctx.policy.attack_radius}"

        if not await self._is_barbarian(target, tx, ty):
            return "alvo não é aldeia bárbara conhecida; agentes só saqueiam bárbaras"

        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
        if await self.repo.attacks_since(ctx.id, since) >= ctx.policy.max_attacks_per_hour:
            return f"limite de {ctx.policy.max_attacks_per_hour} ataques por hora atingido"

        if await self.repo.attacked_recently(target, ctx.policy.retarget_minutes):
            return f"{target} já foi atacado nos últimos {ctx.policy.retarget_minutes} min"

        return None

    async def _is_barbarian(self, target: str, x: int, y: int) -> bool:
        row = (
            await self.session.execute(select(WorldVillage).where(WorldVillage.x == x, WorldVillage.y == y))
        ).scalar_one_or_none()
        if row is not None:
            return row.player_id == 0

        farm = (
            await self.session.execute(
                select(FarmTarget).where(FarmTarget.coords == target, FarmTarget.enabled.is_(True))
            )
        ).scalar_one_or_none()

        return farm is not None
