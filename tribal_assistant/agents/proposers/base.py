"""A specialist that observes the village and proposes actions instead of executing them."""

from abc import ABC, abstractmethod

from tribal_assistant.agents.coordination.budget import Reservation
from tribal_assistant.agents.coordination.constraints import Constraint
from tribal_assistant.agents.coordination.proposal import Proposal
from tribal_assistant.agents.coordination.view import CoordinationView


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class Proposer(ABC):
    key: str
    title: str
    observes: str
    delivers: str

    @abstractmethod
    async def propose(self, view: CoordinationView) -> list[Proposal]:
        """Structured proposals for this round."""

    async def constraints(self, view: CoordinationView) -> list[Constraint]:
        return []

    async def reservations(self, view: CoordinationView) -> list[Reservation]:
        return []

    def urgency_from_hours(self, hours: float, horizon: float = 6.0) -> float:
        if hours == float("inf"):
            return 0.0

        return clamp(1 - hours / horizon)
