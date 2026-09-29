"""Chooses the village role: manual choice wins, otherwise derived from progress; attacks force emergency."""

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.agents.context import VillageContext
from tribal_assistant.agents.coordination.estimates import Estimator
from tribal_assistant.agents.coordination.strategy import Role
from tribal_assistant.repositories.coordination import CoordinationRepository

NOBLE_PATH = (("main", 20), ("smith", 20), ("market", 10))


class RoleSelector:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = CoordinationRepository(session)

    async def select(self, ctx: VillageContext) -> tuple[Role, Role, str]:
        """Returns (base role, mode for this round, reason)."""
        row = await self.repo.strategy(ctx.id)

        if row is not None and row.manual:
            base, reason = Role(row.role), f"escolhido pelo jogador: {row.reason}".strip(": ")
        else:
            base, reason = self.derive(ctx)
            if row is None or row.role != base.value:
                await self.repo.set_strategy(ctx.id, base.value, reason, manual=False)

        if Estimator(ctx).incoming():
            return base, Role.EMERGENCY, "ataque chegando: modo emergência até o impacto"

        return base, base, reason

    @staticmethod
    def derive(ctx: VillageContext) -> tuple[Role, str]:
        levels = ctx.levels
        progress = sum(min(1.0, levels.get(b, 0) / lvl) for b, lvl in NOBLE_PATH) / len(NOBLE_PATH)

        if progress >= 0.8:
            return Role.EXPANSION, f"caminho da academia em {progress:.0%}: preparar nobre"

        return Role.GROWTH, "início de jogo: produção primeiro"
