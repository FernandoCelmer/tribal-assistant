"""Read-only view of what reports and spies taught about a barbarian target."""

import re
from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.core.agents.target_intel import TargetIntel
from tribal_assistant.core.agents.tools.base import AgentTool, ToolOutcome

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox

COORDS = re.compile(r"^\d{1,3}\|\d{1,3}$")


class GetTargetIntel(AgentTool):
    name = "get_target_intel"
    description = (
        "O que se sabe de um alvo bárbaro, em JSON: muralha, recursos espionados e há quantas horas, se a "
        "espionagem ainda vale (nenhum saque depois dela), defensores restantes, último resultado, saque médio, "
        "sequência amarela e perdas. Sem espionagem, envie send_spy antes de saquear alvos grandes."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"coords": {"type": "string", "description": "Coordenadas x|y do alvo, ex.: 498|503."}},
        "required": ["coords"],
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        coords = str(args["coords"]).strip()
        if not COORDS.match(coords):
            return ToolOutcome(False, f"coordenada inválida: {coords!r}")

        data = await box.lessons.target(coords)
        if not data:
            return ToolOutcome(True, f"nada conhecido sobre {coords}; espione com send_spy (1 explorador) antes de saquear")

        return ToolOutcome(True, self.dump(TargetIntel.summary(coords, data)))
