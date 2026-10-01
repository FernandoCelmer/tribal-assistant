"""Browse the game like a player: open a few informative pages and read them."""

from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.core.agents.knobs import tuning
from tribal_assistant.core.agents.sightings import SightingBook
from tribal_assistant.core.agents.tools.base import AgentTool, ToolOutcome
from tribal_assistant.core.game.wander import SAFE_SCREENS

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox


class BrowseGame(AgentTool):
    name = "browse_game"
    description = "Passeia pelo jogo: abre páginas informativas (ranking, perfis de vizinhos, tribos, mapa, relatórios) e lê cada uma."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "stops": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "properties": {
                        "screen": {"type": "string", "enum": sorted(SAFE_SCREENS)},
                        "params": {"type": "object"},
                        "label": {"type": "string", "maxLength": 60},
                    },
                    "required": ["screen"],
                },
            },
            "reason": {"type": "string"},
        },
        "required": ["stops"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        result = await box.actions.wander.tour(box.ctx.game_id, list(args["stops"]))
        read = (result.data or {}).pop("read", [])
        if not result.ok or not read:
            return ToolOutcome(result.ok, result.detail, result.data)

        notes = await SightingBook(box.session).learn(read, tuning(box))
        learned = f" · aprendeu: {'; '.join(notes[:4])}" if notes else " · nada mudou desde a última visita"
        return ToolOutcome(True, result.detail + learned, {**result.data, "learned": notes})
