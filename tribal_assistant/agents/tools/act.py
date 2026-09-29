"""Tools that change the game. Each one passes the guardrails before touching the browser."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.agents.tools.base import AgentTool, ToolOutcome

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox

REASON = {"type": "string", "description": "Motivo curto da decisão (registrado no log)."}


class UpgradeBuilding(AgentTool):
    name = "upgrade_building"
    description = (
        "Coloca o próximo nível de um edifício na fila de construção. Recusado se a fila estiver cheia, "
        "faltar recurso/população/requisito ou o edifício não for da sua área."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "building": {"type": "string", "description": "Id do edifício: main, wood, stone, iron, farm, storage..."},
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
        "Recruta tropas. A quantidade é reduzida para caber no orçamento (reserva de recursos, "
        "fração máxima para recrutar e população livre)."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "unit": {"type": "string", "description": "spear, sword, axe, archer, spy, light, marcher, heavy, ram, catapult"},
            "count": {"type": "integer", "minimum": 1},
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
        "Envia um ataque de saque a uma aldeia BÁRBARA dentro do raio permitido. Recusado para "
        "jogadores, alvos atacados há pouco, tropas insuficientes ou limite de ataques por hora."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Coordenadas x|y do alvo."},
            "units": {
                "type": "object",
                "description": "Tropas por unidade, ex.: {\"light\": 5} ou {\"spear\": 10}.",
                "additionalProperties": {"type": "integer", "minimum": 1},
            },
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
        "Desbloqueia o próximo nível de coleta na praça de reunião (1 Pequena, 2 Média, 3 Grande, "
        "4 Extrema). Custa recursos e leva um tempo; coleta dá recursos sem arriscar tropas."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "option_id": {"type": "integer", "minimum": 1, "maximum": 4},
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
        "Manda tropas coletar recursos num nível de coleta desbloqueado e livre. As tropas não podem "
        "ser chamadas de volta até terminar. Use o nível mais alto livre e deixe tropas para saque se precisar."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "option_id": {"type": "integer", "minimum": 1, "maximum": 4},
            "units": {
                "type": "object",
                "description": "Tropas por unidade, ex.: {\"spear\": 10}.",
                "additionalProperties": {"type": "integer", "minimum": 1},
            },
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
    description = "Coleta todas as recompensas de missão prontas; os recursos entram nesta aldeia."
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


class CompleteQuest(AgentTool):
    name = "complete_quest"
    description = "Conclui uma missão cujas metas já foram atingidas (botão Missão completa)."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"quest_id": {"type": "string"}, "reason": REASON},
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
        "Máximo 12 passos, do mais importante ao menos."
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
                        "target": {"type": "string"},
                        "amount": {"type": "integer", "minimum": 1},
                        "reason": {"type": "string"},
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


class SetVillageGoal(AgentTool):
    name = "set_village_goal"
    description = "Define o objetivo estratégico da aldeia que os outros agentes seguem nas próximas rodadas."
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
