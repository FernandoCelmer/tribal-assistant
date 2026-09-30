"""Farm assistant tools: read the screen, save templates A and B, and raid a barbarian with one of them."""

from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.core.agents.knobs import knob
from tribal_assistant.core.agents.knowledge import UNITS
from tribal_assistant.core.agents.tools.act import REASON
from tribal_assistant.core.agents.tools.base import AgentTool, ToolOutcome
from tribal_assistant.core.game.scraper.farm_assistant import TEMPLATES, FarmAssistantParser

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox

UNAVAILABLE = "farm_unavailable"
FORBIDDEN = ("snob", "militia")
TEMPLATE_UNITS = {
    "type": "object",
    "description": 'Tropas do modelo por id de unidade; unidade ausente fica 0. Ex.: {"light": 5}.',
    "additionalProperties": {"type": "integer", "minimum": 0},
}


class ReadFarmAssistant(AgentTool):
    name = "read_farm_assistant"
    description = (
        "Lê o Assistente de Saque (am_farm) desta aldeia em JSON: se está disponível, os modelos A e B, as tropas "
        "em casa e os alvos da lista com id da aldeia, coordenadas, distância, muralha, recursos vistos, cor do "
        "último relatório, carga cheia e quais botões A/B/C estão ativos. Alimenta o que se sabe dos alvos."
    )

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if box.dry_run:
            return ToolOutcome(True, "(simulação) assistente de saque não lido", {"available": False})

        memory = f"{UNAVAILABLE}:{box.ctx.game_id}"
        if not await box.lessons.due(memory, knob(box.ctx, "farm.recheck_hours")):
            return ToolOutcome(True, "assistente de saque indisponível (visto há pouco)", {"available": False})

        state = await box.actions.farm.state(box.ctx.game_id)
        if not state.get("available"):
            await box.lessons.mark(memory, str(state.get("reason", "")))
            return ToolOutcome(True, f"assistente de saque indisponível: {state.get('reason')}", state)

        state["learned"] = await box.lessons.farm_list(state.get("targets") or [])
        summary = {
            "templates": {k: FarmAssistantParser.squad(state, k) for k in TEMPLATES},
            "home": {u: n for u, n in (state.get("home") or {}).items() if n},
            "targets": state.get("targets") or [],
        }
        return ToolOutcome(True, self.dump(summary), state)


class SetFarmTemplates(AgentTool):
    name = "set_farm_templates"
    description = (
        "Salva os modelos A e B do Assistente de Saque desta aldeia e confere que o jogo guardou. A = grupo pequeno "
        "para bárbaras sem muralha; B = grupo maior para carga cheia recorrente ou muralha 1-2 (só cavalaria). "
        "Nunca ativa nem estende conta premium. RECUSADO com unidade desconhecida ou nobre."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"a": TEMPLATE_UNITS, "b": TEMPLATE_UNITS, "reason": REASON},
        "required": ["reason"],
        "additionalProperties": False,
    }
    acts = True

    @staticmethod
    def refusal(wanted: dict[str, dict[str, int]]) -> str | None:
        if not wanted:
            return "informe o modelo a, b ou os dois"

        for letter, units in wanted.items():
            for unit, count in units.items():
                if unit not in UNITS or unit in FORBIDDEN:
                    return f"modelo {letter.upper()}: unidade {unit!r} não pode ir no assistente"
                if count < 0:
                    return f"modelo {letter.upper()}: quantidade negativa de {unit}"

        return None

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        wanted = {k: {str(u): int(n) for u, n in dict(args[k]).items()} for k in TEMPLATES if k in args}
        refusal = self.refusal(wanted)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) modelos {wanted}", {"templates": wanted})

        result = await box.actions.farm.set_templates(box.ctx.game_id, wanted)
        return ToolOutcome(result.ok, result.detail, {"templates": wanted, **{k: v for k, v in result.data.items() if k == "notices"}})


class SendFarmTemplate(AgentTool):
    name = "send_farm_template"
    description = (
        "Saqueia uma aldeia BÁRBARA da lista do Assistente de Saque clicando no botão A ou B da linha dela. Use "
        "target_id e coords de read_farm_assistant. Mesmas travas de send_farm_attack: RECUSADO para jogadores, "
        "linha que não é bárbara em world_villages, alvo atacado há pouco, fora do raio, tropas insuficientes ou "
        "limite de ataques por hora."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Coordenadas x|y do alvo, ex.: 498|503."},
            "target_id": {"type": "integer", "minimum": 1, "description": "Id da aldeia-alvo na lista do assistente."},
            "template": {"type": "string", "enum": ["a", "b"], "description": "Modelo: a (pequeno) ou b (maior)."},
            "units": {**TEMPLATE_UNITS, "description": "Tropas do modelo como lidas em read_farm_assistant (opcional)."},
            "reason": REASON,
        },
        "required": ["target", "target_id", "template", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        target = str(args["target"]).strip()
        target_id = int(args["target_id"])
        letter = str(args["template"]).lower()
        if letter not in TEMPLATES:
            return ToolOutcome(False, f"RECUSADO: modelo {letter!r} desconhecido; use a ou b")

        units = {str(u): int(n) for u, n in dict(args.get("units") or {}).items() if int(n) > 0}
        if not units and not box.dry_run:
            units = FarmAssistantParser.squad(await box.actions.farm.state(box.ctx.game_id), letter)

        refusal = await box.guard.check_farm_template(box.ctx, target, target_id, units)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            result_ok, detail = True, f"(simulação) saque modelo {letter.upper()} para {target}"
        else:
            result = await box.actions.farm.send(box.ctx.game_id, target_id, target, letter, units)
            result_ok, detail = result.ok, result.detail

        if result_ok:
            for unit, count in units.items():
                current = box.ctx.unit(unit)
                if current is not None:
                    current.home -= count
                    current.away += count

        return ToolOutcome(result_ok, detail, {"target": target, "target_id": target_id, "template": letter, "units": units})
