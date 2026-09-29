"""Read-only tools: village state, quests, game knowledge, barbarian targets."""

from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.core.agents.knowledge import GameKnowledge
from tribal_assistant.core.agents.tools.base import AgentTool, ToolOutcome
from tribal_assistant.core.errors import DomainError
from tribal_assistant.core.services.world import WorldService

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox


class GetVillageState(AgentTool):
    name = "get_village_state"
    description = (
        "Estado atual resumido da aldeia: recursos, fila, edifícios, tropas, coleta, missões, plano e ataques "
        "(o mesmo do início da conversa, atualizado após suas ações). Só chame para conferir o efeito de uma ação."
    )

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        from tribal_assistant.core.agents.view import ContextView

        return ToolOutcome(True, ContextView(box.ctx, box.ctx.policy.build_queue_slots).render(box.agent.key))


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
        "ou um guia completo (kind=guide, id=inicio, avancado, nobre ou tribo). "
        "Use só em caso de dúvida; o jogo tem a palavra final."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["building", "unit", "strategy", "guide"], "description": "O que consultar."},
            "id": {"type": "string", "description": "Id do edifício (main, barracks, snob...) ou da unidade (spear, light...); inicio, avancado, nobre ou tribo para guide; vazio para strategy."},
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


class SearchDocs(AgentTool):
    name = "search_docs"
    description = (
        "Busca na biblioteca local (ajuda oficial, guias e tutoriais do fórum) e devolve os trechos mais relevantes "
        "com o caminho do documento. Use para dúvidas de regra, custo, estratégia ou mecânica do jogo."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 2, "description": "Pergunta ou palavras-chave em português."},
            "category": {"type": "string", "description": "Opcional: help, forum, guides ou search."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 8},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        from tribal_assistant.core.services.docs import DocsService

        hits = await DocsService(box.session).search(str(args["query"]), int(args.get("limit") or 4), args.get("category"))
        if not hits:
            return ToolOutcome(True, "nada encontrado na biblioteca; tente outras palavras")

        return ToolOutcome(True, "\n\n".join(f"[{h.path}] {h.title}{' · ' + h.section if h.section else ''}\n{h.text[:900]}" for h in hits))


class ReadDoc(AgentTool):
    name = "read_doc"
    description = "Lê um documento inteiro da biblioteca pelo caminho que search_docs devolveu (ex.: help/academia.md)."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"path": {"type": "string", "minLength": 3}},
        "required": ["path"],
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        from tribal_assistant.core.errors import NotFoundError
        from tribal_assistant.core.services.docs import DocsService

        try:
            doc = await DocsService(box.session).read(str(args["path"]))
        except NotFoundError as exc:
            return ToolOutcome(False, exc.message)

        return ToolOutcome(True, f"{doc.title}\n\n{doc.text[:12000]}")


class ListBarbarians(AgentTool):
    name = "list_barbarians"
    description = (
        "Aldeias bárbaras dentro do raio de ataque, da mais perto para a mais longe, em JSON com coords, pontos, "
        "distância, minutos de viagem por unidade e recently_attacked (pule essas). "
        "Chame uma vez antes de send_farm_attack."
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
        radius = min(int(args.get("radius") or box.ctx.policy.attack_radius), box.ctx.policy.attack_radius)
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
                "recently_attacked": await box.repo.attacked_recently(r.coords, box.ctx.policy.retarget_minutes),
                **{k: v for k, v in (await box.lessons.target(r.coords)).items() if k in ("last_result", "avg_haul", "attacks", "yellow_streak")},
            }
            for r in rows
        ]

        if not targets:
            return ToolOutcome(True, "nenhuma bárbara conhecida; sincronize o mundo (world sync)")

        return ToolOutcome(True, self.dump(targets))
