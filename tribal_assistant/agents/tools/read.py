"""Read-only tools: village state, quests, game knowledge, barbarian targets."""

from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import select

from tribal_assistant.agents.knowledge import GameKnowledge
from tribal_assistant.agents.tools.base import AgentTool, ToolOutcome
from tribal_assistant.core.errors import DomainError
from tribal_assistant.models.farm_target import FarmTarget
from tribal_assistant.services.world import WorldService

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox


class GetVillageState(AgentTool):
    name = "get_village_state"
    description = (
        "Estado atual resumido da aldeia: recursos, fila, edifícios, tropas, coleta, missões, plano e ataques "
        "(o mesmo do início da conversa, atualizado após suas ações). Só chame para conferir o efeito de uma ação."
    )

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        from tribal_assistant.agents.view import ContextView

        return ToolOutcome(True, ContextView(box.ctx, box.config.build_queue_slots).render(box.agent.key))


class GetQuests(AgentTool):
    name = "get_quests"
    description = (
        "Missões ativas em JSON com metas, progresso (current/target) e can_complete, e quantas recompensas "
        "estão prontas. O resumo já está no estado; chame só se precisar do detalhe das metas."
    )

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        return ToolOutcome(
            True, self.dump({"quests": box.ctx.quests, "rewards_pending": box.ctx.rewards_pending})
        )


class LookupKnowledge(AgentTool):
    name = "lookup_knowledge"
    description = (
        "Fatos do jogo (ajuda oficial): requisitos, nível máximo e papel de um edifício; custo, população, "
        "velocidade, carga, ataque/defesa e requisito de uma unidade; a estratégia de base (kind=strategy); "
        "ou um guia completo (kind=guide, id=inicio, avancado ou nobre). "
        "Use só em caso de dúvida; o jogo tem a palavra final."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["building", "unit", "strategy", "guide"], "description": "O que consultar."},
            "id": {"type": "string", "description": "Id do edifício (main, barracks, snob...) ou da unidade (spear, light...); inicio, avancado ou nobre para guide; vazio para strategy."},
        },
        "required": ["kind"],
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        kind = args.get("kind")
        key = str(args.get("id", ""))

        if kind == "strategy":
            return ToolOutcome(True, GameKnowledge.strategy)

        if kind == "guide":
            text = GameKnowledge.guide(key)
            if text is None:
                return ToolOutcome(False, f"guia {key!r} desconhecido; use {', '.join(GameKnowledge.guides)}")

            return ToolOutcome(True, text)

        info = GameKnowledge.building(key) if kind == "building" else GameKnowledge.unit(key)
        if info is None:
            return ToolOutcome(False, f"{kind} {key!r} desconhecido")

        return ToolOutcome(True, self.dump(info))


class ListBarbarians(AgentTool):
    name = "list_barbarians"
    description = (
        "Aldeias bárbaras dentro do raio de ataque, da mais perto para a mais longe, em JSON com coords, pontos, "
        "distância, minutos de viagem por unidade e recently_attacked (pule essas). Usa a lista local de "
        "farm quando faltam dados do mundo. Chame uma vez antes de send_farm_attack."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "radius": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Raio em campos; limitado ao raio de ataque."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 30, "description": "Máximo de alvos (padrão 10)."},
        },
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        radius = min(int(args.get("radius") or box.config.attack_radius), box.config.attack_radius)
        limit = int(args.get("limit") or 10)

        try:
            rows = await WorldService(box.session).nearby(box.ctx.id, "barbarian", radius, limit)
        except DomainError:
            rows = []

        targets = [
            {
                "coords": r.coords,
                "points": r.points,
                "distance": r.distance,
                "minutes": r.travel_minutes,
                "recently_attacked": await box.repo.attacked_recently(r.coords, box.config.retarget_minutes),
            }
            for r in rows
        ]

        if not targets:
            farm = (
                await box.session.execute(select(FarmTarget).where(FarmTarget.enabled.is_(True)))
            ).scalars()
            targets = [
                {
                    "coords": f.coords,
                    "source": "farm_targets",
                    "recently_attacked": await box.repo.attacked_recently(f.coords, box.config.retarget_minutes),
                }
                for f in farm
            ]

        if not targets:
            return ToolOutcome(True, "nenhuma bárbara conhecida; sincronize o mundo (world sync)")

        return ToolOutcome(True, self.dump(targets))
