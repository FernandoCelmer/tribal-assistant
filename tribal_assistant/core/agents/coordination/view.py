"""Everything a proposer may read for one village: state, forecasts, lessons, game reads and guardrails."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.coordination.estimates import Estimator
from tribal_assistant.core.agents.coordination.insight import Insight
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.guardrails import Guardrails
from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.learning import LessonBook
from tribal_assistant.core.game.actions import GameActions
from tribal_assistant.core.schemas.agent_settings import AgentSettings

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox


@dataclass
class CoordinationView:
    ctx: VillageContext
    session: AsyncSession
    config: AgentSettings
    actions: GameActions
    dry_run: bool
    role: Role
    base_role: Role
    reader: "Toolbox"
    estimator: Estimator = field(init=False)
    guard: Guardrails = field(init=False)
    lessons: LessonBook = field(init=False)
    insights: list[Insight] = field(default_factory=list)
    satisfied: set[str] = field(default_factory=set)
    note_error: str = ""
    recent: set[str] = field(default_factory=set)
    knobs: Knobs = field(default_factory=Knobs)
    siblings: list[VillageContext] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.estimator = Estimator(self.ctx)
        self.guard = Guardrails(self.session, self.config)
        self.lessons = LessonBook(self.session)

    @property
    def free_slots(self) -> int:
        return max(0, self.ctx.policy.build_queue_slots - len(self.ctx.queue))

    def build_cost(self, building: str) -> dict[str, int]:
        b = self.ctx.building(building)
        if b is None:
            return {}

        return {"wood": b.next_wood or 0, "clay": b.next_clay or 0, "iron": b.next_iron or 0, "pop": b.next_pop or 0}

    def unit_cost(self, unit: str, count: int) -> dict[str, int]:
        u = self.ctx.unit(unit)
        if u is None:
            return {}

        return {
            "wood": (u.cost_wood or 0) * count,
            "clay": (u.cost_clay or 0) * count,
            "iron": (u.cost_iron or 0) * count,
            "pop": (u.cost_pop or 0) * count,
        }

    @property
    def others(self) -> list[VillageContext]:
        """The other own villages of this account."""
        return [s for s in self.siblings if s.id != self.ctx.id]

    async def read(self, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        return await self.reader.invoke(tool, arguments or {})

    async def cooldown(self, name: str, hours: float | None = None) -> bool:
        """Once per tuned interval (knob cooldown.<name>) for this village."""
        if not await self.due(name, hours):
            return False

        await self.mark(name)
        return True

    async def due(self, name: str, hours: float | None = None) -> bool:
        """Whether the tuned interval passed, without starting a new one."""
        return await self.lessons.due(f"{name}:{self.ctx.game_id}", hours if hours is not None else self.knobs.get(f"cooldown.{name}"))

    async def mark(self, name: str) -> None:
        await self.lessons.mark(f"{name}:{self.ctx.game_id}")

    def note(self, insight: Insight) -> None:
        self.insights.append(insight)
