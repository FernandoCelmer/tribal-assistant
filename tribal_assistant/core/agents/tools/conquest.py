"""The conquest tool: nobles with escort against one barbarian, alone or as a train in the same second."""

from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.core.agents.conquest import ConquestBook
from tribal_assistant.core.agents.knobs import knob_int
from tribal_assistant.core.agents.tools.act import REASON, UNITS
from tribal_assistant.core.agents.tools.base import AgentTool, ToolOutcome

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox


class SendNoble(AgentTool):
    name = "send_noble"
    description = (
        "Manda nobres para conquistar uma aldeia BÁRBARA: cada ataque leva 1 nobre e a mesma escolta; com vários nobres "
        "saem juntos num trem, no mesmo segundo. Limpe o alvo antes. RECUSADO para jogadores, sem nobre em casa, escolta "
        "abaixo do mínimo, fora do raio ou com ataque chegando."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Coordenadas x|y da bárbara, ex.: 498|503."},
            "nobles": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Quantos nobres no trem."},
            "escort": UNITS | {"description": "Escolta de CADA nobre, sem o nobre. Ex.: {\"axe\": 200}."},
            "reason": REASON,
        },
        "required": ["target", "nobles", "escort", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        target = str(args["target"]).strip()
        nobles = int(args["nobles"])
        escort = {str(k): int(v) for k, v in dict(args["escort"]).items() if int(v) > 0}

        refusal = await box.guard.check_noble(box.ctx, target, nobles, escort)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        waves = [{"snob": 1, **escort} for _ in range(nobles)]
        data = {"target": target, "nobles": nobles, "escort": escort}
        if box.dry_run:
            result_ok, detail = True, f"(simulação) {nobles} nobre(s) para {target} com {escort} cada"
        else:
            x, y = (int(part) for part in target.split("|"))
            result = await box.actions.conquest.send_train(box.ctx.game_id, x, y, waves)
            result_ok, detail = result.ok, result.detail

        if result_ok:
            for wave in waves:
                for unit, count in wave.items():
                    current = box.ctx.unit(unit)
                    current.home -= count
                    current.away += count

            if not box.dry_run:
                state = await ConquestBook(box.session).sent(target, box.ctx.id, nobles, knob_int(box.ctx, "conquest.loyalty_hit"))
                data["loyalty"] = state["loyalty"]

        return ToolOutcome(result_ok, detail, data)
