"""Defense reads: incoming attacks with origin and likely slowest unit, and the battle simulator."""

from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.core.agents.coordination.incoming import DodgePlanner, IncomingWatch
from tribal_assistant.core.agents.knowledge import UNITS
from tribal_assistant.core.agents.tools.base import AgentTool, ToolOutcome
from tribal_assistant.core.game.battle import simulate_battle

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox

ARMY: dict[str, Any] = {
    "type": "object",
    "properties": {u: {"type": "integer", "minimum": 0} for u in UNITS},
    "additionalProperties": False,
}


class GetIncoming(AgentTool):
    name = "get_incoming"
    description = (
        "Ataques chegando nesta aldeia em JSON: origem, jogador, chegada, minutos restantes, distância, "
        "unidade mais lenta provável (pelo tempo de viagem), rótulo (espião, CL, CP, infantaria, espadachim, "
        "aríete, nobre ou fake), exército estimado e a decisão sugerida (hold, dodge ou ignore) com o motivo."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"village": {"type": "string", "description": "Opcional: coordenadas x|y da aldeia; padrão a aldeia atual."}},
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        village = str(args.get("village") or "").strip()
        if village and village != box.ctx.village.coords:
            return ToolOutcome(False, f"só leio ataques da aldeia atual ({box.ctx.village.coords})")

        watch = IncomingWatch(box.session)
        attacks = await watch.attacks(box.ctx)
        if not attacks:
            return ToolOutcome(True, "nenhum ataque chegando")

        planner = DodgePlanner(box.session, await watch.clock())
        rows = []
        for attack in attacks:
            decision = planner.decide(box.ctx, attack)
            rows.append(attack.to_dict() | {"decision": decision.action, "why": decision.reason})

        return ToolOutcome(True, self.dump(rows))


class SimulateBattle(AgentTool):
    name = "simulate_battle"
    description = (
        "Simula uma batalha com a fórmula do jogo (sem sorte nem moral): ataque por tipo contra a defesa "
        "correspondente, muralha multiplica a defesa, vencedor perde (menor/maior)^1.5. Devolve quem vence e as perdas."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "attacker": ARMY,
            "defender": ARMY,
            "wall": {"type": "integer", "minimum": 0, "maximum": 20},
        },
        "required": ["attacker", "defender"],
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        attacker = {str(k): int(v) for k, v in dict(args["attacker"]).items() if int(v) > 0}
        defender = {str(k): int(v) for k, v in dict(args["defender"]).items() if int(v) > 0}
        result = simulate_battle(attacker, defender, int(args.get("wall") or 0))
        return ToolOutcome(True, self.dump(result.to_dict()))
