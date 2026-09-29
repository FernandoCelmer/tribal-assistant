"""Base class for everything an agent can call."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.ai.types import ToolSpec

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox


@dataclass
class ToolOutcome:
    ok: bool
    text: str
    data: dict[str, Any] = field(default_factory=dict)


class AgentTool(ABC):
    """One capability. `acts=True` tools change the game and are logged as decisions."""

    name: str
    description: str
    parameters: ClassVar[dict[str, Any]] = {"type": "object", "properties": {}, "additionalProperties": False}
    acts: bool = False

    @staticmethod
    def dump(data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, default=str)

    def spec(self) -> ToolSpec:
        return ToolSpec(self.name, self.description, self.parameters)

    @abstractmethod
    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        """Execute with validated arguments against the toolbox's village."""
