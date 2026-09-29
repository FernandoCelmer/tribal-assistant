"""Read-only planning tools: forecasts, scavenging split and own market offers."""

from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.core.agents.tools.base import AgentTool, ToolOutcome

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox

AMOUNT = {"type": "integer", "minimum": 0}


class GetForecast(AgentTool):
    name = "get_forecast"
    description = (
        "Previsão da aldeia pelo ritmo atual: horas até cada recurso encher o armazém, até a população travar, "
        "até a fila acabar e até o próximo ataque chegar; quando dá para pagar a próxima obra do plano e, se "
        "informado, um custo (wood, clay, iron). Horas nulas significam nunca."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"wood": AMOUNT, "clay": AMOUNT, "iron": AMOUNT},
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        from tribal_assistant.core.services.forecast import ForecastService

        cost = {r: int(args.get(r) or 0) for r in ("wood", "clay", "iron")}
        forecast = await ForecastService(box.session).build(box.ctx, cost)
        return ToolOutcome(True, forecast.model_dump_json(), forecast.model_dump(mode="json"))


class PlanScavenge(AgentTool):
    name = "plan_scavenge"
    description = (
        "Divide as tropas em casa entre os níveis de coleta livres para render mais recurso por minuto, com todas "
        "as coletas terminando juntas (cada parte com a população mínima). Devolve as tropas por nível para "
        "send_scavenge. Opcional: `units` limita quais tropas usar."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "units": {
                "type": "object",
                "description": 'Máximo por unidade a usar, ex.: {"spear": 40}. Vazio usa todas em casa.',
                "additionalProperties": {"type": "integer", "minimum": 0},
            }
        },
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        from tribal_assistant.core.services.forecast import ScavengePlanner

        plan = ScavengePlanner.plan(box.ctx, args.get("units") or None)
        return ToolOutcome(True, plan.model_dump_json(), plan.model_dump(mode="json"))


class GetOwnOffers(AgentTool):
    name = "get_own_offers"
    description = (
        "Ofertas próprias abertas no mercado desta aldeia: id, recurso dado e pedido, quantidades, lotes e se é "
        "ferro estacionado (pede mais do que dá). Use o id em cancel_market_offer."
    )

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if box.dry_run:
            return ToolOutcome(True, "(simulação) ofertas próprias não lidas")

        offers = await box.actions.market.list_own_offers(box.ctx.game_id)
        for offer in offers:
            offer["parked"] = offer["buy_amount"] > offer["sell_amount"]

        return ToolOutcome(True, self.dump(offers) if offers else "nenhuma oferta própria aberta", {"offers": offers})
