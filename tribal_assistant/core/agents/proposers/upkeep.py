"""Steward: account upkeep the player would click by hand, proposed with low cost and clear value."""

import re
from typing import Any, ClassVar

from loguru import logger

from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import Knobs, tuning
from tribal_assistant.core.agents.proposers.base import Proposer

TRAINING_COST = {21: 100, 22: 200, 23: 400, 24: 700, 25: 1000}
UNIT_BONUS = {"lanceiro": "spear", "espadachim": "sword", "machado": "axe", "arqueiro": "archer", "cavalaria leve": "light", "cavalaria pesada": "heavy"}


class UpkeepProposer(Proposer):
    key = "steward"
    title = "Mordomo"
    observes = "relíquias, bandeiras, paladino, inventário, forja do evento e missões simples"
    delivers = "bônus grátis aplicados sem gastar pontos premium"

    RELIC_PRODUCTION: ClassVar[int] = 2
    FLAG_PRIORITY: ClassVar[tuple[int, ...]] = (1, 6, 2, 8, 4, 3, 5, 7)
    SKILL_PRIORITY: ClassVar[tuple[int, ...]] = (5, 6, 7, 8, 1, 2, 3, 4, 9, 10, 11, 12)
    TRAINING: ClassVar[tuple[tuple[int, int], ...]] = ((25, 1000), (24, 700), (23, 400), (22, 200), (21, 100))

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        if view.dry_run:
            return []

        items: list[Proposal] = []
        for step in (self._relic, self._flag, self._knight, self._items, self._forge, self._name):
            try:
                items += await step(view)
            except Exception as exc:
                view.note_error = str(exc)
                logger.warning("Passo do administrador {} falhou: {}", step.__name__, exc)

        return items

    def _free(self, action: str, arguments: dict[str, Any], reason: str, benefit: str, impact: float, cost: dict[str, int] | None = None, key: str = "") -> Proposal:
        return Proposal(
            self.key,
            action,
            {**arguments, "reason": reason[:60]},
            reason,
            benefit,
            cost=cost or {},
            factors=Factors(urgency=0.4, impact=impact, opportunity=0.7),
            horizon=Horizon.IMMEDIATE,
            confidence=0.9,
            key=key,
        )

    async def _forge(self, view: CoordinationView) -> list[Proposal]:
        from tribal_assistant.core.game.forge import Forge

        if not await view.cooldown("forge"):
            return []

        state = await view.actions.forge.state(view.ctx.game_id)
        if not state.get("active"):
            return []

        amounts = {m: int(v.get("amount", 0)) for m, v in state.get("materials", {}).items()}
        materials = Forge.pick(amounts, state.get("recipes", {}))
        if materials is None:
            return []

        new = "-".join(materials) not in state.get("recipes", {})
        reason = "fórmula nova na forja do evento" if new else "material grátis parado na forja"
        return [self._free("craft_event_item", {"materials": materials}, reason, "item do evento, ranking diário e conquista da Antiga Forja", 0.5)]

    async def _relic(self, view: CoordinationView) -> list[Proposal]:
        if not await view.cooldown("relic"):
            return []

        return [
            self._free("choose_relic", {"index": self.RELIC_PRODUCTION}, "relíquia inicial de produção", "+5% madeira", 0.6),
            self._free("equip_relic", {}, "espaço de relíquia livre", "bônus da relíquia na aldeia", 0.55, key="equip_relic"),
        ]

    async def _flag(self, view: CoordinationView) -> list[Proposal]:
        if not await view.cooldown("flag"):
            return []

        state = await view.actions.flags(view.ctx.game_id)
        if state.get("current"):
            return []

        best = self.best_flag([tuple(pair) for pair in state.get("owned", [])])
        if best is None:
            return []

        return [self._free("assign_flag", {"flag_type": best[0], "level": best[1]}, "melhor bandeira disponível", "bônus permanente da bandeira", 0.6)]

    @classmethod
    def best_flag(cls, owned: list[tuple[int, int]]) -> tuple[int, int] | None:
        for flag_type in cls.FLAG_PRIORITY:
            levels = [level for t, level in owned if t == flag_type]
            if levels:
                return flag_type, max(levels)

        return None

    async def _knight(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        if ctx.levels.get("statue", 0) < 1 or not await view.cooldown("knight"):
            return []

        state = await view.actions.knight_state(ctx.game_id)
        items = []

        if state.get("can_recruit"):
            items.append(self._free("recruit_knight", {}, "paladino barato e forte", "unidade forte e de saque", 0.7, cost={"wood": 20, "clay": 20, "iron": 40, "pop": 10}))

        for skill in sorted(state.get("learnable", []), key=self.skill_rank)[:1]:
            items.append(self._free("learn_knight_skill", {"skill_id": skill}, "ponto de habilidade livre", f"habilidade {skill}", 0.5))

        regimen = self.training(ctx.stock, ctx.village.storage, tuning(view)) if state.get("can_train") else None
        if regimen:
            price = TRAINING_COST[regimen]
            proposal = self._free("train_knight", {"regimen": regimen}, "recursos sobrando viram XP", "paladino sobe de nível", 0.35, cost={"wood": price, "clay": price, "iron": price})
            proposal.factors.opportunity_cost = 0.3
            items.append(proposal)

        return items

    @classmethod
    def skill_rank(cls, skill: int) -> int:
        return cls.SKILL_PRIORITY.index(skill) if skill in cls.SKILL_PRIORITY else len(cls.SKILL_PRIORITY)

    @classmethod
    def training(cls, stock: dict[str, int], storage: int, knobs: Knobs | None = None) -> int | None:
        knobs = knobs or Knobs()
        multiple, full = knobs.get("knight.train_stock_multiple"), knobs.get("knight.train_full_share")
        lowest = min(stock.get(r, 0) for r in ("wood", "clay", "iron"))
        for regimen, cost in cls.TRAINING:
            if cost * multiple <= lowest or (storage and lowest >= storage * full and cost <= lowest * 0.5):
                return regimen

        return None

    async def _items(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        if not await view.cooldown("items"):
            return []

        inventory = await view.actions.inventory(ctx.game_id)
        await view.lessons.repo.observe("inventory", "inventory", "Inventário", f"{len(inventory)} item(ns)", {"items": inventory})
        attacked = bool(view.estimator.incoming())
        home = {u.name: u.home for u in ctx.village.units}

        items = []
        for item in inventory:
            decision = self.item_decision(item, ctx.stock, ctx.village.storage, bool(ctx.queue), attacked, home, tuning(view))
            if decision:
                items.append(self._free("use_item", {"key": item["key"]}, decision, str(item.get("name")), 0.5))

        return items

    @staticmethod
    def item_decision(
        item: dict[str, Any], stock: dict[str, int], storage: int, building: bool, attacked: bool = False, home: dict[str, int] | None = None, knobs: Knobs | None = None
    ) -> str | None:
        knobs = knobs or Knobs()
        name = str(item.get("name") or "")
        detail = str(item.get("detail") or "")
        if not item.get("usable"):
            return None

        unit = next((u for label, u in UNIT_BONUS.items() if label in name.lower()), None)
        if unit:
            return f"bônus de {unit} com ataque chegando" if attacked and (home or {}).get(unit, 0) >= knobs.int("items.unit_bonus_min") else None

        if "livro" in name.lower() or "livro de habilidade" in detail.lower():
            return "livro de habilidade libera habilidade do paladino"

        if "Construção" in name or "construção" in detail:
            return "bônus de construção com fila ocupada" if building else None

        match = re.search(r"(\d+)%\s*da capacidade", detail)
        if match:
            gain = storage * int(match.group(1)) // 100
            room = min(storage - stock.get(r, 0) for r in ("wood", "clay", "iron"))
            if storage >= knobs.int("items.pack_min_storage") and gain <= room:
                return f"pacote de recursos cabe no armazém (+{gain})"

        return None

    async def _name(self, view: CoordinationView) -> list[Proposal]:
        ctx = view.ctx
        if not any(q["id"] == "1400" for q in ctx.quests) or not await view.cooldown("rename"):
            return []

        player = (ctx.player or {}).get("name") or "Aldeia"
        return [self._free("rename_village", {"name": f"{player} 001"}, "missão: Um nome digno", "recompensa da missão", 0.5)]
