"""Hard limits every agent action passes through, whatever the model decided."""

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.accounts.context import current_account_id
from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.knobs import knob, knob_int
from tribal_assistant.core.agents.knowledge import UNITS, GameKnowledge
from tribal_assistant.core.agents.logistics import CARRY, Merchants
from tribal_assistant.core.models.agent import AgentDecision
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.models.world import WorldVillage
from tribal_assistant.core.repositories.agents import AgentRepository
from tribal_assistant.core.schemas.agent_settings import AgentSettings

RAID_ACTIONS = ("send_farm_attack", "send_farm_template", "send_spy")


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
        least = knob_int(ctx, "scavenge.min_pop")
        if pop < least:
            return f"coleta exige pelo menos {least} de população; as tropas somam {pop}"

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
        near_full = any(value >= storage * knob(ctx, "storage.near_full_share") for value in ctx.stock.values())
        budget_share = max(ctx.policy.recruit_budget, knob(ctx, "recruit.near_full_budget")) if near_full else ctx.policy.recruit_budget

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

    async def check_attack(self, ctx: VillageContext, target: str, units: dict[str, int], dodge: bool = False) -> str | None:
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
        dodging = dodge and any(c["direction"] == "in" and c["kind"] in ("attack", "noble") for c in ctx.commands)
        radius = knob_int(ctx, "dodge.radius") if dodging else ctx.policy.attack_radius
        if distance > radius:
            return f"alvo a {distance:.1f} campos; limite {radius}"

        if not await self._is_barbarian(target, tx, ty):
            return "alvo não é aldeia bárbara conhecida; agentes só saqueiam bárbaras"

        if dodging:
            return None

        if await self.attacks_last_hour(ctx) >= ctx.policy.max_attacks_per_hour:
            return f"limite de {ctx.policy.max_attacks_per_hour} ataques por hora atingido"

        if await self.repo.attacked_recently(target, ctx.policy.retarget_minutes):
            return f"{target} já foi atacado nos últimos {ctx.policy.retarget_minutes} min"

        return None

    async def check_farm_template(self, ctx: VillageContext, target: str, target_id: int, units: dict[str, int]) -> str | None:
        """The same limits as a raid from the rally point, plus the assistant row must be the barbarian of world_villages."""
        if not units:
            return "modelo vazio no assistente de saque"

        refusal = await self.check_attack(ctx, target, units)
        if refusal:
            return refusal

        row = (await self.session.execute(select(WorldVillage).where(WorldVillage.id == int(target_id)))).scalar_one_or_none()
        if row is None or row.player_id != 0:
            return f"aldeia {target_id} da lista do assistente não é bárbara em world_villages; agentes só saqueiam bárbaras"

        if f"{row.x}|{row.y}" != target:
            return f"aldeia {target_id} fica em {row.x}|{row.y}, não em {target}"

        return None

    async def check_spy(self, ctx: VillageContext, target: str, count: int) -> str | None:
        """A scouting probe: barbarians only, inside the radius and the hourly limit; the game decides the squad size."""
        try:
            tx, ty = (int(part) for part in target.split("|"))
            ox, oy = (int(part) for part in ctx.village.coords.split("|"))
        except ValueError:
            return f"coordenada inválida: {target!r}"

        spy = ctx.unit("spy")
        if spy is None or spy.home < count:
            return f"só há {spy.home if spy else 0} exploradores em casa"

        distance = math.hypot(tx - ox, ty - oy)
        if distance > ctx.policy.attack_radius:
            return f"alvo a {distance:.1f} campos; limite {ctx.policy.attack_radius}"

        if not await self._is_barbarian(target, tx, ty):
            return "alvo não é aldeia bárbara conhecida; espiões só vão a bárbaras"

        if await self.attacks_last_hour(ctx) >= ctx.policy.max_attacks_per_hour:
            return f"limite de {ctx.policy.max_attacks_per_hour} ataques por hora atingido"

        if await self.spied_recently(target, ctx.policy.retarget_minutes):
            return f"{target} já foi espionado nos últimos {ctx.policy.retarget_minutes} min"

        return None

    async def own_village(self, village_id: int) -> Village | None:
        """A village of this same account, never another player's."""
        row = (await self.session.execute(select(Village).where(Village.id == village_id))).scalar_one_or_none()
        account = current_account_id()
        if row is None or not row.is_own or (account is not None and row.account_id != account):
            return None

        return row

    async def check_send_resources(self, ctx: VillageContext, to_village_id: int, amounts: dict[str, int], merchants: dict[str, int]) -> str | None:
        """Shipments only between own villages of this account, within free merchants and above the origin floor."""
        if to_village_id == ctx.id:
            return "origem e destino são a mesma aldeia"

        target = await self.own_village(to_village_id)
        if target is None:
            return f"aldeia {to_village_id} não é sua nesta conta; recursos só vão para aldeias próprias"

        if any(v < 0 for v in amounts.values()) or sum(amounts.values()) <= 0:
            return "nenhum recurso informado"

        if ctx.levels.get("market", 0) < 1:
            return "aldeia sem mercado"

        needed = Merchants.needed(amounts, merchants.get("carry") or CARRY)
        if needed > merchants.get("free", 0):
            return f"comerciantes livres {merchants.get('free', 0)}, precisa de {needed}"

        floor = max(self.reserve(ctx), int((ctx.village.storage or 0) * knob(ctx, "logistics.keep_share")))
        for resource, amount in amounts.items():
            if amount and ctx.stock.get(resource, 0) - amount < floor:
                return f"{resource} ficaria abaixo da reserva de {floor} da origem"

        cap = int((target.storage or 0) * knob(ctx, "logistics.dest_fill_share"))
        for resource, amount in amounts.items():
            if target.storage and amount and getattr(target, resource, 0) + amount > cap:
                return f"{resource} estouraria o armazém de {target.name}"

        return None

    async def check_noble(self, ctx: VillageContext, target: str, nobles: int, escort: dict[str, int]) -> str | None:
        """Nobles only against barbarians, only with nobles at home and never without the minimum escort."""
        try:
            tx, ty = (int(part) for part in target.split("|"))
            ox, oy = (int(part) for part in ctx.village.coords.split("|"))
        except ValueError:
            return f"coordenada inválida: {target!r}"

        if nobles < 1 or nobles > knob_int(ctx, "conquest.train_max"):
            return f"trem usa de 1 a {knob_int(ctx, 'conquest.train_max')} nobres"

        snob = ctx.unit("snob")
        if snob is None or snob.home < nobles:
            return f"só há {snob.home if snob else 0} nobre(s) em casa"

        if "snob" in escort:
            return "a escolta não leva nobre"

        least = knob_int(ctx, "conquest.escort_pop")
        if sum(UNITS[u].pop * n for u, n in escort.items() if u in UNITS) < least:
            return f"escolta abaixo de {least} de população por nobre"

        for unit, count in escort.items():
            current = ctx.unit(unit)
            if current is None or current.home < count * nobles:
                return f"só há {current.home if current else 0} {unit} em casa para {nobles} escolta(s)"

        distance = math.hypot(tx - ox, ty - oy)
        if distance > knob_int(ctx, "expansion.target_radius"):
            return f"alvo a {distance:.1f} campos; limite {knob_int(ctx, 'expansion.target_radius')}"

        if not await self._is_barbarian(target, tx, ty):
            return "alvo não é aldeia bárbara conhecida; nobres só conquistam bárbaras"

        if any(c["direction"] == "in" and c["kind"] in ("attack", "noble") for c in ctx.commands):
            return "ataque chegando; nobres ficam em casa"

        return None

    async def attacks_last_hour(self, ctx: VillageContext) -> int:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
        stmt = select(func.count(AgentDecision.id)).where(
            AgentDecision.village_id == ctx.id,
            AgentDecision.action.in_(RAID_ACTIONS),
            AgentDecision.ok.is_(True),
            AgentDecision.dry_run.is_(False),
            AgentDecision.created_at >= since,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def spied_recently(self, target: str, minutes: int) -> bool:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=minutes)
        stmt = select(AgentDecision.arguments).where(
            AgentDecision.action == "send_spy",
            AgentDecision.ok.is_(True),
            AgentDecision.dry_run.is_(False),
            AgentDecision.created_at >= since,
        )
        return any(json.loads(raw or "{}").get("target") == target for raw in (await self.session.execute(stmt)).scalars())

    async def _is_barbarian(self, target: str, x: int, y: int) -> bool:
        row = (
            await self.session.execute(select(WorldVillage).where(WorldVillage.x == x, WorldVillage.y == y))
        ).scalar_one_or_none()
        if row is None or row.player_id != 0:
            return False

        own = (await self.session.execute(select(Village.id).where(Village.coords == target, Village.is_own.is_(True)))).first()
        return own is None
