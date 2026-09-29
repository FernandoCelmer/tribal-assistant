"""How an agent decides: rules or a language model."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tribal_assistant.agents.roles.base import VillageAgent
    from tribal_assistant.agents.toolbox import Toolbox


class Brain(ABC):
    name: str

    @abstractmethod
    async def act(self, agent: "VillageAgent", box: "Toolbox") -> str:
        """Run the agent for one village and return a short summary."""
