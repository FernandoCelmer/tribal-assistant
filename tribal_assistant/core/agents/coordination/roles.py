"""Chooses the village role automatically every round; a manual choice wins; attacks force emergency."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.estimates import Estimator
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.coordination.threat import ThreatScan
from tribal_assistant.core.agents.learning import LessonBook
from tribal_assistant.core.models.command import Command
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.repositories.coordination import CoordinationRepository

NOBLE_PATH = (("main", 20), ("smith", 20), ("market", 10))
PROTECTION_WARNING_HOURS = 48
CONFIRM_ROUNDS = 3


class RoleSelector:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CoordinationRepository(session)
        self.lessons = LessonBook(session)

    async def select(self, ctx: VillageContext) -> tuple[Role, Role, str]:
        """Returns (base role, mode for this round, reason)."""
        row = await self.repo.strategy(ctx.id)

        if row is not None and row.manual:
            base, reason = Role(row.role), f"escolhido pelo jogador: {row.reason}".strip(": ")
        else:
            wanted, reason = await self.evaluate(ctx)
            base = await self._confirm(ctx, Role(row.role) if row else None, wanted)
            if base != wanted:
                reason = f"mantém {base.value} até {wanted.value} se confirmar ({reason})"
            if row is None or row.role != base.value:
                await self.repo.set_strategy(ctx.id, base.value, reason, manual=False)

        if Estimator(ctx).incoming():
            return base, Role.EMERGENCY, "ataque chegando: modo emergência até o impacto"

        return base, base, reason

    async def evaluate(self, ctx: VillageContext) -> tuple[Role, str]:
        facts = await self.facts(ctx)
        return self.decide(ctx, facts)

    async def facts(self, ctx: VillageContext) -> dict[str, Any]:
        scan = ThreatScan(self.session)
        threats = await scan.near(ctx)
        dangerous = scan.dangerous(threats, ctx.village.points)

        own = (await self.session.execute(select(Village.id).where(Village.is_own.is_(True)))).scalars().all()
        under_attack = (
            await self.session.execute(
                select(Command.village_id).where(Command.direction == "in").where(Command.kind.in_(("attack", "noble")))
            )
        ).scalars().all()

        targets = await self.lessons.repo.list("target", limit=50)
        good_targets = sum(1 for t in targets if json.loads(t.data or "{}").get("last_result") == "green")

        return {
            "dangerous": dangerous,
            "own_villages": len(own),
            "others_under_attack": [v for v in under_attack if v != ctx.id],
            "good_targets": good_targets,
            "protection_hours": self.protection_hours(ctx),
        }

    @staticmethod
    def protection_hours(ctx: VillageContext) -> float | None:
        until = (ctx.player or {}).get("protection_until")
        if not until:
            return None

        end = datetime.fromisoformat(str(until).replace("Z", "+00:00"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)

        return (end - datetime.now(UTC)).total_seconds() / 3600

    @staticmethod
    def decide(ctx: VillageContext, facts: dict[str, Any]) -> tuple[Role, str]:
        levels = ctx.levels
        dangerous = facts.get("dangerous", [])
        protection = facts.get("protection_hours")
        light = ctx.unit("light")

        if dangerous and (protection is None or protection <= PROTECTION_WARNING_HOURS):
            nearest = dangerous[0]
            when = "proteção acabando" if protection and protection > 0 else "sem proteção"
            return Role.DEFENSE, f"{when} e {nearest.player} ({nearest.points} pts) a {nearest.distance} campos"

        if facts.get("others_under_attack") and facts.get("own_villages", 1) >= 2:
            return Role.SUPPORT, "outra aldeia sua está sob ataque: produzir e mandar defesa"

        progress = sum(min(1.0, levels.get(b, 0) / lvl) for b, lvl in NOBLE_PATH) / len(NOBLE_PATH)
        if progress >= 0.8:
            return Role.EXPANSION, f"caminho da academia em {progress:.0%}: preparar nobre"

        if light and light.total >= 20 and facts.get("good_targets", 0) >= 3 and not dangerous:
            return Role.OFFENSIVE, f"{light.total} cavalarias leves e {facts['good_targets']} alvos bons: saque constante"

        return Role.GROWTH, "produção primeiro: sem ameaça próxima nem exército de saque"

    async def _confirm(self, ctx: VillageContext, current: Role | None, wanted: Role) -> Role:
        """Switch only after the same wish repeats for a few rounds; defense switches at once."""
        if current is None or wanted == current or wanted == Role.DEFENSE:
            await self.lessons.repo.observe(f"role_wish:{ctx.id}", "cooldown", wanted.value, "", {"role": wanted.value, "count": 0})
            return wanted

        row = await self.lessons.repo.get(f"role_wish:{ctx.id}")
        data = json.loads(row.data) if row else {}
        count = data.get("count", 0) + 1 if data.get("role") == wanted.value else 1
        await self.lessons.repo.observe(f"role_wish:{ctx.id}", "cooldown", wanted.value, "", {"role": wanted.value, "count": count})

        return wanted if count >= CONFIRM_ROUNDS else current

    @staticmethod
    def derive(ctx: VillageContext) -> tuple[Role, str]:
        return RoleSelector.decide(ctx, {})
