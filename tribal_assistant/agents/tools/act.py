"""Tools that change the game. Each one passes the guardrails before touching the browser."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.agents.tools.base import AgentTool, ToolOutcome

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox

REASON = {"type": "string", "description": "Motivo curto (até 8 palavras), registrado no log. Ex.: \"missão: Bosque 5\"."}
UNITS = {
    "type": "object",
    "description": "Tropas por id de unidade, só as que estão em casa. Ex.: {\"light\": 5} ou {\"spear\": 10}.",
    "additionalProperties": {"type": "integer", "minimum": 1},
}
TIER = {"type": "integer", "minimum": 1, "maximum": 4, "description": "Nível de coleta: 1 Pequena, 2 Média, 3 Grande, 4 Extrema."}


class UpgradeBuilding(AgentTool):
    name = "upgrade_building"
    description = (
        "Coloca o próximo nível (um por chamada) de um edifício na fila de construção. Use só edifícios "
        "marcados \"pode\" no estado. RECUSADO se já estiver na fila, a fila estiver cheia, estiver no "
        "nível máximo, faltar requisito, recurso ou população, ou o edifício não for da sua área nem do plano."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "building": {"type": "string", "description": "Id do edifício: main, barracks, stable, garage, smith, snob, market, wood, stone, iron, farm, storage, hide, wall, statue, watchtower."},
            "reason": REASON,
        },
        "required": ["building", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        building = str(args["building"])

        from tribal_assistant.agents.plan import PlanTracker

        planned = building in PlanTracker.next_builds(box.ctx.plan)
        if box.agent.buildings and building not in box.agent.buildings and not planned:
            return ToolOutcome(False, f"RECUSADO: {building} não é da área do {box.agent.title}")

        refusal = box.guard.check_upgrade(box.ctx, building)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        current = box.ctx.building(building)

        if box.dry_run:
            result_ok, detail = True, f"(simulação) {building} → nível {current.next_level}"
        else:
            result = await box.actions.upgrade_building(box.ctx.game_id, building, box.config.auto_finish_free)
            result_ok, detail = result.ok, result.detail

        if result_ok:
            box.ctx.spend(current.next_wood or 0, current.next_clay or 0, current.next_iron or 0, current.next_pop or 0)
            current.queued_level = current.next_level

        return ToolOutcome(result_ok, detail, {"building": building, "level": current.next_level})


class RecruitUnits(AgentTool):
    name = "recruit_units"
    description = (
        "Recruta tropas nesta aldeia. A quantidade é reduzida para caber no orçamento (recursos acima da "
        "reserva vezes a fração de recrutamento, população livre e máximo do jogo), nunca aumentada. "
        "RECUSADO se a unidade não estiver pesquisada ou não houver orçamento."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "unit": {
                "type": "string",
                "enum": ["spear", "sword", "axe", "archer", "spy", "light", "marcher", "heavy", "ram", "catapult"],
                "description": "Id da unidade; só as marcadas como recrutáveis no estado.",
            },
            "count": {"type": "integer", "minimum": 1, "description": "Quantidade desejada; pode ser reduzida."},
            "reason": REASON,
        },
        "required": ["unit", "count", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        unit = str(args["unit"])
        plan = box.guard.plan_recruit(box.ctx, unit, int(args["count"]))

        if plan.refusal:
            return ToolOutcome(False, f"RECUSADO: {plan.refusal}")

        if box.dry_run:
            result_ok, detail, count = True, f"(simulação) {plan.count} {unit}", plan.count
        else:
            result = await box.actions.recruit(box.ctx.game_id, unit, plan.count)
            result_ok, detail = result.ok, result.detail
            count = int(result.data.get("count", plan.count))

        if result_ok:
            current = box.ctx.unit(unit)
            box.ctx.spend(
                (current.cost_wood or 0) * count,
                (current.cost_clay or 0) * count,
                (current.cost_iron or 0) * count,
                (current.cost_pop or 0) * count,
            )

        return ToolOutcome(result_ok, detail, {"unit": unit, "count": count})


class SendFarmAttack(AgentTool):
    name = "send_farm_attack"
    description = (
        "Envia um ataque de saque a uma aldeia BÁRBARA (sem dono) dentro do raio permitido; use alvos de "
        "list_barbarians com recently_attacked=false. Grupo típico: 5 light ou 10 spear. RECUSADO para "
        "jogadores, alvos atacados há pouco, fora do raio, tropas insuficientes ou limite de ataques por hora."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Coordenadas x|y do alvo, ex.: 498|503."},
            "units": UNITS,
            "reason": REASON,
        },
        "required": ["target", "units", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        target = str(args["target"]).strip()
        units = {str(k): int(v) for k, v in dict(args["units"]).items() if int(v) > 0}

        refusal = await box.guard.check_attack(box.ctx, target, units)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            result_ok, detail, arrival = True, f"(simulação) ataque para {target}", None
        else:
            x, y = (int(part) for part in target.split("|"))
            result = await box.actions.send_attack(box.ctx.game_id, x, y, units)
            result_ok, detail, arrival = result.ok, result.detail, result.data.get("arrival")

        if result_ok:
            for unit, count in units.items():
                current = box.ctx.unit(unit)
                current.home -= count
                current.away += count

        return ToolOutcome(result_ok, detail, {"target": target, "units": units, "arrival": arrival})


class UnlockScavenge(AgentTool):
    name = "unlock_scavenge"
    description = (
        "Começa a desbloquear um nível de coleta na praça de reunião. Custa recursos e leva um tempo; "
        "coleta dá recursos sem arriscar tropas. Níveis em ordem (1 antes do 2) e um de cada vez: "
        "RECUSADO se já estiver livre ou desbloqueando, outro estiver desbloqueando ou o anterior estiver bloqueado."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "option_id": TIER,
            "reason": REASON,
        },
        "required": ["option_id", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        option_id = int(args["option_id"])

        refusal = box.guard.check_unlock_scavenge(box.ctx, option_id)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) desbloquear coleta {option_id}", {"option_id": option_id})

        result = await box.actions.unlock_scavenge(box.ctx.game_id, option_id)
        if result.ok:
            option = next(o for o in box.ctx.village.scavenge if o.option_id == option_id)
            option.unlock_at = option.unlock_at or option.return_at or datetime.now(UTC)
            cost = result.data.get("cost", {})
            box.ctx.spend(cost.get("wood", 0), cost.get("clay", 0), cost.get("iron", 0))

        return ToolOutcome(result.ok, result.detail, result.data)


class SendScavenge(AgentTool):
    name = "send_scavenge"
    description = (
        "Manda tropas coletar recursos num nível de coleta desbloqueado e livre (\"livre\" no estado). "
        "Não há perdas, mas as tropas não voltam até terminar. Use o nível mais alto livre e deixe tropas "
        "para saque e defesa. RECUSADO com ataque chegando, nível ocupado ou bloqueado, ou tropas insuficientes."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "option_id": TIER,
            "units": UNITS,
            "reason": REASON,
        },
        "required": ["option_id", "units", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        option_id = int(args["option_id"])
        units = {str(k): int(v) for k, v in dict(args["units"]).items() if int(v) > 0}

        refusal = box.guard.check_scavenge(box.ctx, option_id, units)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            result_ok, detail = True, f"(simulação) coleta {option_id} com {units}"
        else:
            result = await box.actions.send_scavenge(box.ctx.game_id, option_id, units)
            result_ok, detail = result.ok, result.detail

        if result_ok:
            for unit, count in units.items():
                current = box.ctx.unit(unit)
                current.home -= count
                current.away += count

            option = next(o for o in box.ctx.village.scavenge if o.option_id == option_id)
            option.return_at = option.return_at or datetime.now(UTC)

        return ToolOutcome(result_ok, detail, {"option_id": option_id, "units": units})


class ClaimQuestRewards(AgentTool):
    name = "claim_quest_rewards"
    description = (
        "Coleta todas as recompensas de missão prontas (\"recompensas prontas\" no estado); os recursos "
        "entram nesta aldeia. Chame depois de complete_quest. Falha se não houver recompensa pendente."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"reason": REASON},
        "required": ["reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if box.ctx.rewards_pending <= 0:
            return ToolOutcome(False, "nenhuma recompensa pendente")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) coletar {box.ctx.rewards_pending} recompensa(s)")

        result = await box.actions.claim_rewards(box.ctx.game_id)
        if result.ok:
            box.ctx.rewards_pending = 0

        return ToolOutcome(result.ok, result.detail, result.data)


class OpenDailyBonus(AgentTool):
    name = "open_daily_bonus"
    description = (
        "Abre os baús grátis do bônus diário do perfil; os itens vão para o inventário. Vale para a conta "
        "inteira e é verificado no máximo a cada 4 horas. Nunca usa pontos premium."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"reason": REASON},
        "required": ["reason"],
        "additionalProperties": False,
    }
    acts = True
    COOLDOWN_HOURS: ClassVar[int] = 4
    last_check: ClassVar[datetime | None] = None

    @classmethod
    def due(cls) -> bool:
        now = datetime.now(UTC)
        return cls.last_check is None or (now - cls.last_check).total_seconds() >= cls.COOLDOWN_HOURS * 3600

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if not self.due():
            return ToolOutcome(False, "bônus diário já verificado há pouco")

        if box.dry_run:
            return ToolOutcome(True, "(simulação) abrir baús do bônus diário")

        result = await box.actions.open_daily_bonus(box.ctx.game_id)
        type(self).last_check = datetime.now(UTC)

        return ToolOutcome(result.ok, result.detail, result.data)


class CompleteQuest(AgentTool):
    name = "complete_quest"
    description = (
        "Conclui uma missão marcada [pronta] no estado (botão Missão completa). Depois, colete com "
        "claim_quest_rewards. Falha se a missão não existir ou as metas não estiverem atingidas."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "quest_id": {"type": "string", "description": "Id da missão, o primeiro campo de cada missão no estado."},
            "reason": REASON,
        },
        "required": ["quest_id", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        quest_id = str(args["quest_id"])
        quest = next((q for q in box.ctx.quests if q["id"] == quest_id), None)

        if quest is None:
            return ToolOutcome(False, f"missão {quest_id} não encontrada")

        if not quest["can_complete"]:
            return ToolOutcome(False, f"missão {quest_id} ainda não concluída")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) concluir missão {quest_id}")

        result = await box.actions.complete_quest(box.ctx.game_id, quest_id)
        if result.ok:
            quest["can_complete"] = False

        return ToolOutcome(result.ok, result.detail, result.data)


class SetVillagePlan(AgentTool):
    name = "set_village_plan"
    description = (
        "Grava o plano da aldeia: lista ordenada de passos que os outros agentes executam sem IA. "
        "kind: build (target = id do edifício, amount = nível a atingir), recruit (target = unidade, "
        "amount = total de tropas a ter) ou unlock_scavenge (target = nível de coleta 1-4, amount = 1). "
        "Máximo 12 passos, do mais importante ao menos. Substitui o plano atual; passos inválidos são ignorados."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Estratégia em 1-3 frases."},
            "steps": {
                "type": "array",
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "enum": ["build", "recruit", "unlock_scavenge"]},
                        "target": {"type": "string", "description": "Id do edifício, id da unidade ou nível de coleta \"1\"-\"4\"."},
                        "amount": {"type": "integer", "minimum": 1, "description": "Nível a atingir, total de tropas ou 1."},
                        "reason": {"type": "string", "description": "Por que este passo, poucas palavras."},
                    },
                    "required": ["kind", "target", "amount"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["summary", "steps"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        from tribal_assistant.agents.knowledge import GameKnowledge
        from tribal_assistant.agents.plan import PlanTracker
        from tribal_assistant.repositories.plans import PlanRepository
        from tribal_assistant.schemas.plan import PlanStep

        steps, rejected = [], []
        for raw in list(args.get("steps", []))[:12]:
            kind, target, amount = raw.get("kind"), str(raw.get("target", "")), int(raw.get("amount", 0))
            valid = (
                (kind == "build" and target in GameKnowledge.buildings and 1 <= amount <= GameKnowledge.buildings[target].max_level)
                or (kind == "recruit" and target in GameKnowledge.units and 1 <= amount <= 50_000)
                or (kind == "unlock_scavenge" and target in {"1", "2", "3", "4"})
            )
            if valid:
                steps.append(PlanStep(kind=kind, target=target, amount=amount, reason=str(raw.get("reason", ""))[:200]))
            else:
                rejected.append(f"{kind} {target} {amount}")

        if not steps:
            return ToolOutcome(False, "RECUSADO: nenhum passo válido" + (f" ({'; '.join(rejected)})" if rejected else ""))

        summary = str(args.get("summary", "")).strip()[:500]
        await PlanRepository(box.session).save(box.ctx.id, steps, summary=summary, source=box.brain_name, refreshed=True)

        box.ctx.plan = PlanTracker().evaluate(box.ctx, steps)
        box.ctx.plan_summary = summary
        text = f"plano gravado com {len(steps)} passo(s)" + (f"; ignorados: {'; '.join(rejected)}" if rejected else "")

        return ToolOutcome(True, text, {"steps": len(steps), "summary": summary})


class RecruitKnight(AgentTool):
    name = "recruit_knight"
    description = (
        "Recruta um paladino na estátua (custa 20/20/40 e 10 de população, 3h). "
        "Só funciona se a aldeia tiver estátua e ainda não tiver paladino. Nunca usa pontos premium."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"reason": REASON},
        "required": ["reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if box.ctx.levels.get("statue", 0) < 1:
            return ToolOutcome(False, "RECUSADO: aldeia sem estátua")

        knight = box.ctx.unit("knight")
        if knight and knight.total > 0:
            return ToolOutcome(False, "RECUSADO: aldeia já tem paladino")

        if box.dry_run:
            return ToolOutcome(True, "(simulação) recrutar paladino")

        result = await box.actions.recruit_knight(box.ctx.game_id)
        return ToolOutcome(result.ok, result.detail, result.data)


class UseItem(AgentTool):
    name = "use_item"
    description = (
        "Usa um item do inventário pelo botão Usar: pacotes de recurso (somam % da capacidade do armazém, "
        "use quando o armazém for grande e tiver espaço) ou bônus de 24h (construção, unidades). "
        "Use `key` como aparece em get_inventory, ex.: 3057_0."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"key": {"type": "string", "description": "Chave do item, ex.: 3057_0."}, "reason": REASON},
        "required": ["key", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        key = str(args["key"])

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) usar item {key}")

        result = await box.actions.use_item(box.ctx.game_id, key)
        return ToolOutcome(result.ok, result.detail, result.data)


class ChooseRelic(AgentTool):
    name = "choose_relic"
    description = (
        "Escolhe uma das relíquias iniciais da Tesouraria (escolha única). "
        "index 0 bárbaro, 1 lanceiro, 2 produção de recursos, 3 velocidade de recrutamento."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"index": {"type": "integer", "minimum": 0, "maximum": 3}, "reason": REASON},
        "required": ["index", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        index = int(args["index"])

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) escolher relíquia {index}")

        result = await box.actions.choose_relic(box.ctx.game_id, index)
        return ToolOutcome(result.ok, result.detail, result.data)


class EquipRelic(AgentTool):
    name = "equip_relic"
    description = "Equipa a primeira relíquia da Tesouraria no espaço livre desta aldeia (bônus em raio)."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"reason": REASON},
        "required": ["reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if box.dry_run:
            return ToolOutcome(True, "(simulação) equipar relíquia")

        result = await box.actions.equip_relic(box.ctx.game_id)
        return ToolOutcome(result.ok, result.detail, result.data)


class SetVillageGoal(AgentTool):
    name = "set_village_goal"
    description = (
        "Substitui o objetivo estratégico da aldeia, lido por todos os agentes nas próximas rodadas. "
        "Só mude quando a prioridade mudar de fato (ex.: foco no nobre, defesa)."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"goal": {"type": "string", "description": "Objetivo em 1-3 frases, com prioridades."}},
        "required": ["goal"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        goal = str(args["goal"]).strip()
        if not goal:
            return ToolOutcome(False, "objetivo vazio")

        await box.repo.set_goal(box.ctx.id, goal)
        box.ctx.goal = goal

        return ToolOutcome(True, "objetivo registrado", {"goal": goal})
