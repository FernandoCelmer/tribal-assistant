"""Tools that change the game. Each one passes the guardrails before touching the browser."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.core.agents.knobs import Knobs, knob, knob_int
from tribal_assistant.core.agents.knowledge import GameKnowledge
from tribal_assistant.core.agents.logistics import CARRY, Merchants
from tribal_assistant.core.agents.market import MarketRule
from tribal_assistant.core.agents.plan import PlanTracker
from tribal_assistant.core.agents.quests import QuestRules
from tribal_assistant.core.agents.social.ledger import MENTOR, SocialLedger
from tribal_assistant.core.agents.social.rules import SocialRules
from tribal_assistant.core.agents.squads import MIN_POP, UNIT_POP, MinimumSquad
from tribal_assistant.core.agents.tools.base import AgentTool, ToolOutcome
from tribal_assistant.core.repositories.plans import PlanRepository
from tribal_assistant.core.schemas.plan import PlanStep

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox

REASON = {
    "type": "string",
    "description": 'Motivo curto (até 8 palavras), registrado no log. Ex.: "missão: Bosque 5".',
}
UNITS = {
    "type": "object",
    "description": 'Tropas por id de unidade, só as que estão em casa. Ex.: {"light": 5} ou {"spear": 10}.',
    "additionalProperties": {"type": "integer", "minimum": 1},
}
TIER = {
    "type": "integer",
    "minimum": 1,
    "maximum": 4,
    "description": "Nível de coleta: 1 Pequena, 2 Média, 3 Grande, 4 Extrema.",
}


class UpgradeBuilding(AgentTool):
    name = "upgrade_building"
    description = (
        "Coloca o próximo nível (um por chamada) de um edifício na fila de construção. Use só edifícios "
        'marcados "pode" no estado. RECUSADO se já estiver na fila, a fila estiver cheia, estiver no '
        "nível máximo, faltar requisito, recurso ou população, ou o edifício não for da sua área nem do plano."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "building": {
                "type": "string",
                "description": "Id do edifício: main, barracks, stable, garage, smith, snob, market, wood, stone, iron, farm, storage, hide, wall, statue, watchtower.",
            },
            "reason": REASON,
        },
        "required": ["building", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        building = str(args["building"])

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
            result = await box.actions.upgrade_building(
                box.ctx.game_id, building, box.config.auto_finish_free
            )
            result_ok, detail = result.ok, result.detail

        if result_ok:
            box.ctx.spend(
                current.next_wood or 0,
                current.next_clay or 0,
                current.next_iron or 0,
                current.next_pop or 0,
            )
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
                "enum": [
                    "spear",
                    "sword",
                    "axe",
                    "archer",
                    "spy",
                    "light",
                    "marcher",
                    "heavy",
                    "ram",
                    "catapult",
                ],
                "description": "Id da unidade; só as marcadas como recrutáveis no estado.",
            },
            "count": {
                "type": "integer",
                "minimum": 1,
                "description": "Quantidade desejada; pode ser reduzida.",
            },
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

        refusal = await box.guard.check_attack(box.ctx, target, units, dodge=str(args.get("reason", "")).startswith("esquiva"))
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

        return ToolOutcome(
            result_ok, detail, {"target": target, "units": units, "arrival": arrival}
        )


class SendSpy(AgentTool):
    name = "send_spy"
    description = (
        "Sonda uma aldeia BÁRBARA com exploradores (no mínimo o que o mundo exige) para ver muralha, recursos e tropas antes do saque. "
        "Não carrega recursos; conta no limite de ataques por hora. Use em alvos desconhecidos, grandes ou com "
        "resultado amarelo. RECUSADO para jogadores, fora do raio, sem exploradores ou alvo espionado há pouco."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Coordenadas x|y do alvo, ex.: 498|503."},
            "count": {"type": "integer", "minimum": 1, "description": "Exploradores; sobe sozinho para o mínimo do mundo."},
            "reason": REASON,
        },
        "required": ["target", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        target = str(args["target"]).strip()
        count = max(int(args.get("count") or 1), knob_int(box.ctx, "spy.min_send"))

        refusal = await box.guard.check_spy(box.ctx, target, count)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            result_ok, detail, arrival = True, f"(simulação) {count} explorador(es) para {target}", None
        else:
            x, y = (int(part) for part in target.split("|"))
            result = await box.actions.send_attack(box.ctx.game_id, x, y, {"spy": count})
            result_ok, detail, arrival = result.ok, result.detail, result.data.get("arrival")

        needed = MIN_POP.search(detail or "")
        if not result_ok and needed:
            await MinimumSquad(box.session).learn("spy.min_send", int(needed.group(1)), UNIT_POP["spy"])

        if result_ok:
            spy = box.ctx.unit("spy")
            spy.home -= count
            spy.away += count

        return ToolOutcome(result_ok, detail, {"target": target, "units": {"spy": count}, "arrival": arrival})


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
            return ToolOutcome(
                True, f"(simulação) desbloquear coleta {option_id}", {"option_id": option_id}
            )

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
        'Manda tropas coletar recursos num nível de coleta desbloqueado e livre ("livre" no estado). '
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
        'Coleta todas as recompensas de missão prontas ("recompensas prontas" no estado); os recursos '
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
        "inteira e é verificado no intervalo ajustável cooldown.daily_bonus. Nunca usa pontos premium."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"reason": REASON},
        "required": ["reason"],
        "additionalProperties": False,
    }
    acts = True
    last_check: ClassVar[datetime | None] = None

    @classmethod
    def due(cls, hours: float | None = None) -> bool:
        hours = hours if hours is not None else Knobs().get("cooldown.daily_bonus")
        now = datetime.now(UTC)
        return cls.last_check is None or (now - cls.last_check).total_seconds() >= hours * 3600

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if not self.due(knob(box.ctx, "cooldown.daily_bonus")):
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
            "quest_id": {
                "type": "string",
                "description": "Id da missão, o primeiro campo de cada missão no estado.",
            },
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

        if QuestRules.forbidden(quest):
            return ToolOutcome(False, "RECUSADO: missão de milícia corta a produção pela metade; nunca ativar")

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
                        "target": {
                            "type": "string",
                            "description": 'Id do edifício, id da unidade ou nível de coleta "1"-"4".',
                        },
                        "amount": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Nível a atingir, total de tropas ou 1.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Por que este passo, poucas palavras.",
                        },
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
        steps, rejected = [], []
        for raw in list(args.get("steps", []))[:12]:
            kind, target, amount = (
                raw.get("kind"),
                str(raw.get("target", "")),
                int(raw.get("amount", 0)),
            )
            valid = (
                (
                    kind == "build"
                    and target in GameKnowledge.buildings
                    and 1 <= amount <= GameKnowledge.buildings[target].max_level
                )
                or (kind == "recruit" and target in GameKnowledge.units and 1 <= amount <= 50_000)
                or (kind == "unlock_scavenge" and target in {"1", "2", "3", "4"})
            )
            if valid:
                steps.append(
                    PlanStep(
                        kind=kind,
                        target=target,
                        amount=amount,
                        reason=str(raw.get("reason", ""))[:200],
                    )
                )
            else:
                rejected.append(f"{kind} {target} {amount}")

        if not steps:
            return ToolOutcome(
                False,
                "RECUSADO: nenhum passo válido" + (f" ({'; '.join(rejected)})" if rejected else ""),
            )

        summary = str(args.get("summary", "")).strip()[:500]
        await PlanRepository(box.session).save(
            box.ctx.id, steps, summary=summary, source=box.brain_name, refreshed=True
        )

        box.ctx.plan = PlanTracker().evaluate(box.ctx, steps)
        box.ctx.plan_summary = summary
        text = f"plano gravado com {len(steps)} passo(s)" + (
            f"; ignorados: {'; '.join(rejected)}" if rejected else ""
        )

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
        "properties": {
            "key": {"type": "string", "description": "Chave do item, ex.: 3057_0."},
            "reason": REASON,
        },
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
    description = (
        "Equipa a primeira relíquia da Tesouraria no espaço livre desta aldeia (bônus em raio)."
    )
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


class RenameVillage(AgentTool):
    name = "rename_village"
    description = "Muda o nome da aldeia no Edifício Principal (até 32 caracteres). Conclui a missão 'Um nome digno'."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"name": {"type": "string", "maxLength": 32}, "reason": REASON},
        "required": ["name", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        name = str(args["name"]).strip()[:32]
        if not name:
            return ToolOutcome(False, "RECUSADO: nome vazio")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) renomear para {name}")

        result = await box.actions.rename_village(box.ctx.game_id, name)
        return ToolOutcome(result.ok, result.detail, result.data)


class SetProfileText(AgentTool):
    name = "set_profile_text"
    description = "Escreve o texto do perfil do jogador (Configurações → Perfil). Conclui a missão 'A aparência importa'."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"text": {"type": "string", "minLength": 10, "maxLength": 500}, "reason": REASON},
        "required": ["text", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        text = str(args["text"]).strip()[:500]
        if len(text) < 10:
            return ToolOutcome(False, "RECUSADO: texto curto demais")

        if box.dry_run:
            return ToolOutcome(True, "(simulação) salvar texto do perfil")

        result = await box.actions.profile.set_text(box.ctx.game_id, text)
        return ToolOutcome(result.ok, result.detail, result.data)


class AssignFlag(AgentTool):
    name = "assign_flag"
    description = (
        "Atribui uma bandeira possuída a esta aldeia (troca só a cada 24h). Tipos: 1 produção de recursos, "
        "2 velocidade de recrutamento, 3 ataque, 4 defesa, 5 sorte, 6 população, 7 custo de paladino, 8 saque."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "flag_type": {"type": "integer", "minimum": 1, "maximum": 8},
            "level": {"type": "integer", "minimum": 1, "maximum": 9},
            "reason": REASON,
        },
        "required": ["flag_type", "level", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        flag_type, level = int(args["flag_type"]), int(args["level"])

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) atribuir bandeira {flag_type}_{level}")

        result = await box.actions.assign_flag(box.ctx.game_id, flag_type, level)
        return ToolOutcome(result.ok, result.detail, result.data)


class LearnKnightSkill(AgentTool):
    name = "learn_knight_skill"
    description = (
        "Gasta um ponto de habilidade do paladino na estátua. Só habilidades liberadas por livro. "
        "1 Investida (bárbaro +5% ataque), 5 Motivação (+3% madeira), 9 Esgrima (espadachim +5% defesa)."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "skill_id": {"type": "integer", "minimum": 1, "maximum": 12},
            "reason": REASON,
        },
        "required": ["skill_id", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        skill_id = int(args["skill_id"])

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) aprender habilidade {skill_id}")

        result = await box.actions.learn_knight_skill(box.ctx.game_id, skill_id)
        return ToolOutcome(result.ok, result.detail, result.data)


class TrainKnight(AgentTool):
    name = "train_knight"
    description = (
        "Treina o paladino por XP na estátua com recursos (nunca a opção premium -20%). "
        "regimen 21: 500 XP, 100/100/100, 2h; 22: 800 XP, 200 cada, 4h; 23: 1400 XP, 400 cada, 8h; "
        "24: 2200 XP, 700 cada, 12h; 25: 3000 XP, 1000 cada, 24h. O paladino fica indisponível durante o treino."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "regimen": {"type": "integer", "minimum": 21, "maximum": 25},
            "reason": REASON,
        },
        "required": ["regimen", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        regimen = int(args["regimen"])

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) treinar paladino {regimen}")

        result = await box.actions.train_knight(box.ctx.game_id, regimen)
        return ToolOutcome(result.ok, result.detail, result.data)


class CraftEventItem(AgentTool):
    name = "craft_event_item"
    description = (
        "Trabalha um item na forja do evento com 3 materiais grátis do estoque (ids 1-7: Chumbo, Estanho, Cobre, "
        "Ferro, Bronze, Prata, Ouro). Nunca compra material nem usa o passe do evento. Combinação nova descobre fórmula."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "materials": {"type": "array", "items": {"type": "string", "enum": ["1", "2", "3", "4", "5", "6", "7"]}, "minItems": 3, "maxItems": 3},
            "reason": REASON,
        },
        "required": ["materials", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        materials = [str(m) for m in args["materials"]]

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) trabalhar item com {materials}")

        result = await box.actions.forge.craft(box.ctx.game_id, materials)
        return ToolOutcome(result.ok, result.detail, result.data)


class ApplyToTribe(AgentTool):
    name = "apply_to_tribe"
    description = (
        "Envia candidatura a uma tribo (id da tribo) com o texto escrito pela IA a partir dos dados reais da conta; "
        "sem texto não envia. Nunca funda tribo."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "ally_id": {"type": "string", "pattern": "^[0-9]+$"},
            "tag": {"type": "string"},
            "text": {"type": "string", "minLength": 10, "maxLength": 800},
            "reason": REASON,
        },
        "required": ["ally_id", "text", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if (box.ctx.player or {}).get("ally_id"):
            return ToolOutcome(False, "RECUSADO: já está numa tribo")

        ally_id, tag = str(args["ally_id"]), str(args.get("tag") or "")
        text = str(args.get("text") or "").strip()
        if len(text) < 10:
            return ToolOutcome(False, "RECUSADO: candidatura sem texto escrito pela IA a partir dos dados da conta")

        refusal = SocialRules.refusal(text)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) candidatar à tribo {ally_id}")

        result = await box.actions.diplomacy.apply(box.ctx.game_id, ally_id, text)
        if result.ok:
            await SocialLedger(box.session).set_application(ally_id, tag, "pendente")
        return ToolOutcome(result.ok, result.detail, result.data | {"text": text})


class AcceptTribeInvite(AgentTool):
    name = "accept_tribe_invite"
    description = "Aceita um convite recebido para entrar numa tribo."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"invite_id": {"type": "string"}, "reason": REASON},
        "required": ["invite_id", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if (box.ctx.player or {}).get("ally_id"):
            return ToolOutcome(False, "RECUSADO: já está numa tribo")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) aceitar convite {args['invite_id']}")

        result = await box.actions.diplomacy.accept_invite(box.ctx.game_id, str(args["invite_id"]))
        return ToolOutcome(result.ok, result.detail, result.data)


class AcceptMentor(AgentTool):
    name = "accept_mentor"
    description = "Aceita a oferta de um mentor sugerido pelo jogo (vira aprendiz; conta para a conquista Graduado)."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"mentor_id": {"type": "string", "pattern": "^[0-9]+$"}, "name": {"type": "string"}, "reason": REASON},
        "required": ["mentor_id", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if box.dry_run:
            return ToolOutcome(True, f"(simulação) aceitar mentor {args['mentor_id']}")

        result = await box.actions.diplomacy.accept_mentor(box.ctx.game_id, str(args["mentor_id"]))
        if result.ok and args.get("name"):
            await SocialLedger(box.session).note(MENTOR, "mentor", str(args["name"]), {"name": str(args["name"])})
        return ToolOutcome(result.ok, result.detail, result.data)


class AcceptMarketOffer(AgentTool):
    name = "accept_market_offer"
    description = (
        "Aceita uma oferta de outro jogador no mercado: você paga `amount` de `pay` e recebe `receive`. "
        "Recusado se a razão passar de 1, se esvaziar o recurso pago ou se estourar o armazém. Nunca usa a troca premium."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "receive": {"type": "string", "enum": ["wood", "stone", "iron"]},
            "receive_amount": {"type": "integer", "minimum": 1},
            "pay": {"type": "string", "enum": ["wood", "stone", "iron"]},
            "amount": {"type": "integer", "minimum": 1},
            "player": {"type": "string"},
            "reason": REASON,
        },
        "required": ["receive", "receive_amount", "pay", "amount", "player", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        receive, pay = str(args["receive"]), str(args["pay"])
        amount, receive_amount = int(args["amount"]), int(args["receive_amount"])
        stock = {
            "wood": box.ctx.stock.get("wood", 0),
            "stone": box.ctx.stock.get("clay", 0),
            "iron": box.ctx.stock.get("iron", 0),
        }
        storage = box.ctx.village.storage or 0

        refusal = MarketRule.refusal(stock, pay, amount, receive, receive_amount, storage)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            return ToolOutcome(
                True, f"(simulação) trocar {amount} {pay} por {receive_amount} {receive}"
            )

        result = await box.actions.accept_offer(
            box.ctx.game_id, receive, pay, amount, str(args["player"])
        )
        return ToolOutcome(result.ok, result.detail, result.data)


class CreateMarketOffer(AgentTool):
    name = "create_market_offer"
    description = (
        "Cria uma oferta própria no mercado na proporção 1:1 (a única permitida): dá `amount` de `sell` e pede "
        "o mesmo de `buy`. Prende um comerciante até alguém aceitar. Recusado se esvaziar o recurso oferecido."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "sell": {"type": "string", "enum": ["wood", "stone", "iron"]},
            "buy": {"type": "string", "enum": ["wood", "stone", "iron"]},
            "amount": {"type": "integer", "minimum": 100, "maximum": 1000, "multipleOf": 100},
            "max_hours": {"type": "integer", "minimum": 1, "maximum": 96},
            "reason": REASON,
        },
        "required": ["sell", "buy", "amount", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        sell, buy, amount = str(args["sell"]), str(args["buy"]), int(args["amount"])
        stock = {"wood": box.ctx.stock.get("wood", 0), "stone": box.ctx.stock.get("clay", 0), "iron": box.ctx.stock.get("iron", 0)}
        storage = box.ctx.village.storage or 0

        refusal = MarketRule.refusal(stock, sell, amount, buy, amount, storage)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) oferta {amount} {sell} por {amount} {buy}")

        result = await box.actions.create_offer(box.ctx.game_id, sell, amount, buy, int(args.get("max_hours", 5)))
        return ToolOutcome(result.ok, result.detail, result.data)


class ResearchUnit(AgentTool):
    name = "research_unit"
    description = "Pesquisa uma unidade no ferreiro (libera o recrutamento dela). Ex.: axe exige Ferreiro 2; light exige Estábulo."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"unit": {"type": "string", "enum": ["spear", "sword", "axe", "archer", "spy", "light", "marcher", "heavy", "ram", "catapult"]}, "reason": REASON},
        "required": ["unit", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        unit = str(args["unit"])
        if box.ctx.levels.get("smith", 0) < 1:
            return ToolOutcome(False, "RECUSADO: aldeia sem ferreiro")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) pesquisar {unit}")

        result = await box.actions.research(box.ctx.game_id, unit)
        return ToolOutcome(result.ok, result.detail, result.data)


class SetVillageGoal(AgentTool):
    name = "set_village_goal"
    description = (
        "Substitui o objetivo estratégico da aldeia, lido por todos os agentes nas próximas rodadas. "
        "Só mude quando a prioridade mudar de fato (ex.: foco no nobre, defesa)."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Objetivo em 1-3 frases, com prioridades."}
        },
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


class CancelMarketOffer(AgentTool):
    name = "cancel_market_offer"
    description = (
        "Cancela uma oferta própria no mercado desta aldeia e devolve o recurso ao armazém. Use quando o recurso "
        "estacionado for necessário (pesquisa, recrutamento, obra). O id vem de get_own_offers."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"offer_id": {"type": "string", "pattern": "^[0-9]+$"}, "reason": REASON},
        "required": ["offer_id", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        offer_id = str(args["offer_id"]).strip()
        if not offer_id.isdigit():
            return ToolOutcome(False, "RECUSADO: id de oferta inválido")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) cancelar oferta {offer_id}")

        result = await box.actions.market.cancel_offer(box.ctx.game_id, offer_id)
        if result.ok:
            offer = result.data.get("offer", {})
            key = "clay" if offer.get("sell") == "stone" else offer.get("sell")
            if key in box.ctx.stock:
                box.ctx.stock[key] += offer.get("sell_amount", 0) * offer.get("count", 1)

        return ToolOutcome(result.ok, result.detail, result.data)


class ParkMarketOffer(AgentTool):
    name = "park_market_offer"
    description = (
        "Estaciona recurso sobrando em ofertas próprias que quase ninguém aceita (pede o máximo que o mundo permite, "
        "viagem curta): o recurso fica nos comerciantes, não é saqueado nem estoura o armazém. Cancele com "
        "cancel_market_offer quando precisar dele. Recusado se deixar o recurso abaixo do piso iron_parking.floor_share do armazém."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "sell": {"type": "string", "enum": ["wood", "stone", "iron"]},
            "buy": {"type": "string", "enum": ["wood", "stone", "iron"]},
            "amount": {"type": "integer", "minimum": 100, "maximum": 1000, "multipleOf": 100, "description": "Quantidade por oferta (um comerciante)."},
            "lots": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Quantas ofertas iguais."},
            "max_hours": {"type": "integer", "minimum": 1, "maximum": 96},
            "reason": REASON,
        },
        "required": ["sell", "buy", "amount", "lots", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        floor = knob(box.ctx, "iron_parking.floor_share")
        sell, buy = str(args["sell"]), str(args["buy"])
        amount, lots = int(args["amount"]), int(args["lots"])
        key = "clay" if sell == "stone" else sell
        stock = box.ctx.stock.get(key, 0)
        storage = box.ctx.village.storage or 0

        if sell == buy:
            return ToolOutcome(False, "RECUSADO: troca do mesmo recurso")

        if stock - amount * lots < storage * floor:
            return ToolOutcome(False, f"RECUSADO: {sell} ficaria abaixo de {floor:.0%} do armazém")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) estacionar {lots}x {amount} {sell} pedindo {buy}")

        result = await box.actions.market.park(box.ctx.game_id, sell, amount, buy, lots, int(args.get("max_hours") or 1))
        if result.ok:
            box.ctx.stock[key] -= amount * lots

        return ToolOutcome(result.ok, result.detail, result.data)


class SendResources(AgentTool):
    name = "send_resources"
    description = (
        "Envia madeira, argila e ferro pelo mercado desta aldeia para OUTRA ALDEIA SUA da mesma conta (id de aldeia do painel). "
        "Nunca para outros jogadores. RECUSADO se o destino não for aldeia própria, faltar comerciante livre, a origem ficar "
        "abaixo da reserva ou o armazém do destino estourar."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "to_village_id": {"type": "integer", "minimum": 1, "description": "Id da aldeia própria que recebe."},
            "wood": {"type": "integer", "minimum": 0},
            "clay": {"type": "integer", "minimum": 0},
            "iron": {"type": "integer", "minimum": 0},
            "reason": REASON,
        },
        "required": ["to_village_id", "wood", "clay", "iron", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        to = int(args["to_village_id"])
        amounts = {r: int(args.get(r) or 0) for r in ("wood", "clay", "iron")}
        merchants = {"free": Merchants.total(box.ctx.levels.get("market", 0)), "carry": CARRY}

        refusal = await box.guard.check_send_resources(box.ctx, to, amounts, merchants)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        target = await box.guard.own_village(to)
        data = {"to_village_id": to, "target": target.coords, **amounts}
        if box.dry_run:
            return ToolOutcome(True, f"(simulação) enviar {amounts} para {target.name} ({target.coords})", data)

        x, y = (int(part) for part in target.coords.split("|"))
        result = await box.actions.market.send_resources(box.ctx.game_id, x, y, amounts, (box.ctx.player or {}).get("name"))
        if result.ok:
            box.ctx.spend(amounts["wood"], amounts["clay"], amounts["iron"])
            await box.lessons.mark(f"logistics:{to}")

        return ToolOutcome(result.ok, result.detail, data | {k: v for k, v in result.data.items() if k == "notices"})
