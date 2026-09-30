"""Roles shared out across the villages of one account: the exposed one holds, the academy expands, the far stable raids."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.coordination.threat import ThreatScan
from tribal_assistant.core.agents.knobs import Knobs

FAR = float("inf")


@dataclass(frozen=True)
class VillageFacts:
    id: int
    name: str
    exposure: float
    dangerous: bool
    stable: int
    academy: int


class AccountRoles:
    """With two or more villages each one gets the job that fits where it is and what it has built."""

    def __init__(self, session: AsyncSession, knobs: Knobs | None = None) -> None:
        self.session = session
        self.knobs = knobs or Knobs()

    async def facts(self, contexts: list[VillageContext]) -> list[VillageFacts]:
        scan = ThreatScan(self.session, self.knobs)
        items = []
        for ctx in contexts:
            threats = await scan.near(ctx)
            items.append(
                VillageFacts(
                    ctx.id,
                    ctx.village.name,
                    threats[0].distance if threats else FAR,
                    bool(scan.dangerous(threats, ctx.village.points)),
                    ctx.levels.get("stable", 0),
                    ctx.levels.get("snob", 0),
                )
            )

        return items

    async def roles(self, contexts: list[VillageContext]) -> dict[int, tuple[Role, str]]:
        if len(contexts) < 2:
            return {}

        return self.assign(await self.facts(contexts), self.knobs)

    @staticmethod
    def assign(facts: list[VillageFacts], knobs: Knobs | None = None) -> dict[int, tuple[Role, str]]:
        knobs = knobs or Knobs()
        if len(facts) < 2:
            return {}

        roles: dict[int, tuple[Role, str]] = {}
        exposed = min(facts, key=lambda f: (f.exposure, f.id))
        if exposed.exposure <= knobs.get("account.exposed_distance"):
            role = Role.DEFENSE if exposed.dangerous else Role.SUPPORT
            roles[exposed.id] = (role, f"aldeia mais exposta da conta: jogador a {exposed.exposure:g} campos")

        academies = [f for f in facts if f.id not in roles and f.academy >= knobs.int("account.expansion_snob")]
        if academies:
            best = max(academies, key=lambda f: (f.academy, f.exposure, -f.id))
            roles[best.id] = (Role.EXPANSION, "aldeia com academia: nobres e pacotes da conta")

        stables = [f for f in facts if f.id not in roles and f.stable >= knobs.int("account.offensive_stable")]
        if stables:
            far = max(stables, key=lambda f: (f.exposure, f.stable, -f.id))
            where = "sem jogadores por perto" if far.exposure == FAR else f"jogador mais perto a {far.exposure:g} campos"
            roles[far.id] = (Role.OFFENSIVE, f"aldeia mais afastada com estábulo ({where}): saque e limpeza")

        return roles

    @staticmethod
    def merge(wanted: Role, reason: str, assigned: tuple[Role, str] | None, roles: dict[int, tuple[Role, str]]) -> tuple[Role, str]:
        """The village's own alarm wins; an academy path wins unless another village already expands."""
        if assigned is None or wanted in (Role.DEFENSE, Role.SUPPORT):
            return wanted, reason

        if wanted == Role.EXPANSION and not any(role == Role.EXPANSION for role, _ in roles.values()):
            return wanted, reason

        return assigned[0], f"conta: {assigned[1]}"
