"""Account upkeep the player would otherwise click by hand: relics, flags, paladin, items and small quests."""

import re
from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.agents.roles.base import VillageAgent

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox


class StewardAgent(VillageAgent):
    key = "steward"
    title = "Mordomo"
    mission = (
        "Cuidar da conta sem gastar pontos premium: escolher e equipar relíquia de produção, manter a melhor "
        "bandeira atribuída, aprender habilidades do paladino, treiná-lo com recursos que sobram, usar bônus "
        "do inventário na hora certa e cumprir missões simples como renomear a aldeia."
    )
    tools = (
        "choose_relic",
        "equip_relic",
        "assign_flag",
        "learn_knight_skill",
        "train_knight",
        "recruit_knight",
        "use_item",
        "rename_village",
        "accept_market_offer",
    )

    RELIC_PRODUCTION: ClassVar[int] = 2
    FLAG_PRIORITY: ClassVar[tuple[int, ...]] = (1, 6, 2, 8, 4, 3, 5, 7)
    SKILL_PRIORITY: ClassVar[tuple[int, ...]] = (5, 6, 7, 8, 1, 2, 3, 4, 9, 10, 11, 12)
    TRAINING: ClassVar[tuple[tuple[int, int], ...]] = (
        (25, 1000),
        (24, 700),
        (23, 400),
        (22, 200),
        (21, 100),
    )

    def needs_llm(self, ctx, config) -> bool:
        return False

    async def rules(self, box: "Toolbox") -> str:
        done = []

        for step in (self._relic, self._flag, self._knight, self._items, self._name, self._market):
            try:
                note = await step(box)
            except Exception as exc:
                note = f"{step.__name__.strip('_')}: {exc}"

            if note:
                done.append(note)

        return "; ".join(done) or "nada a cuidar agora"

    async def _once(self, box: "Toolbox", name: str, hours: float) -> bool:
        key = f"{name}:{box.ctx.game_id}"
        if not await box.lessons.due(key, hours):
            return False

        await box.lessons.mark(key)
        return True

    async def _relic(self, box: "Toolbox") -> str:
        if not await self._once(box, "relic", 6):
            return ""

        notes = []
        chosen = await box.invoke(
            "choose_relic",
            {"index": self.RELIC_PRODUCTION, "reason": "produção acelera a economia"},
        )
        if chosen.ok:
            notes.append(chosen.text)

        equipped = await box.invoke("equip_relic", {"reason": "espaço de relíquia livre"})
        if equipped.ok:
            notes.append(equipped.text)

        return "; ".join(notes)

    async def _flag(self, box: "Toolbox") -> str:
        if box.dry_run or not await self._once(box, "flag", 6):
            return ""

        state = await box.actions.flags(box.ctx.game_id)
        if state.get("current"):
            return ""

        owned = [tuple(pair) for pair in state.get("owned", [])]
        best = self.best_flag(owned)
        if best is None:
            return ""

        outcome = await box.invoke(
            "assign_flag",
            {"flag_type": best[0], "level": best[1], "reason": "melhor bandeira disponível"},
        )
        return outcome.text if outcome.ok else ""

    @classmethod
    def best_flag(cls, owned: list[tuple[int, int]]) -> tuple[int, int] | None:
        for flag_type in cls.FLAG_PRIORITY:
            levels = [level for t, level in owned if t == flag_type]
            if levels:
                return flag_type, max(levels)

        return None

    async def _knight(self, box: "Toolbox") -> str:
        ctx = box.ctx
        if ctx.levels.get("statue", 0) < 1 or box.dry_run or not await self._once(box, "knight", 1):
            return ""

        state = await box.actions.knight_state(ctx.game_id)
        notes = []

        if state.get("can_recruit"):
            outcome = await box.invoke("recruit_knight", {"reason": "paladino barato e forte"})
            notes.append(outcome.text)

        for skill in sorted(state.get("learnable", []), key=self.skill_rank)[:1]:
            outcome = await box.invoke(
                "learn_knight_skill", {"skill_id": skill, "reason": "ponto de habilidade livre"}
            )
            notes.append(outcome.text)

        regimen = self.training(ctx.stock, ctx.village.storage) if state.get("can_train") else None
        if regimen:
            outcome = await box.invoke(
                "train_knight", {"regimen": regimen, "reason": "recursos sobrando viram XP"}
            )
            notes.append(outcome.text)

        return "; ".join(notes)

    @classmethod
    def skill_rank(cls, skill: int) -> int:
        return (
            cls.SKILL_PRIORITY.index(skill)
            if skill in cls.SKILL_PRIORITY
            else len(cls.SKILL_PRIORITY)
        )

    @classmethod
    def training(cls, stock: dict[str, int], storage: int) -> int | None:
        lowest = min(stock.get(r, 0) for r in ("wood", "clay", "iron"))
        for regimen, cost in cls.TRAINING:
            if cost * 4 <= lowest or (storage and lowest >= storage * 0.8 and cost <= lowest * 0.5):
                return regimen

        return None

    async def _items(self, box: "Toolbox") -> str:
        ctx = box.ctx
        if box.dry_run or not await self._once(box, "items", 3):
            return ""

        notes = []
        for item in await box.actions.inventory(ctx.game_id):
            decision = self.item_decision(item, ctx.stock, ctx.village.storage, bool(ctx.queue))
            if decision:
                outcome = await box.invoke("use_item", {"key": item["key"], "reason": decision})
                notes.append(outcome.text)

        return "; ".join(notes)

    @staticmethod
    def item_decision(
        item: dict[str, Any], stock: dict[str, int], storage: int, building: bool
    ) -> str | None:
        name = str(item.get("name") or "")
        detail = str(item.get("detail") or "")
        if not item.get("usable"):
            return None

        if "Construção" in name or "construção" in detail:
            return "bônus de construção com fila ocupada" if building else None

        match = re.search(r"(\d+)%\s*da capacidade", detail)
        if match:
            gain = storage * int(match.group(1)) // 100
            room = min(storage - stock.get(r, 0) for r in ("wood", "clay", "iron"))
            if storage >= 5000 and gain <= room:
                return f"pacote de recursos cabe no armazém (+{gain})"

        return None

    async def _name(self, box: "Toolbox") -> str:
        ctx = box.ctx
        if not any(q["id"] == "1400" for q in ctx.quests):
            return ""

        if not await self._once(box, "rename", 24):
            return ""

        player = (ctx.player or {}).get("name") or "Aldeia"
        outcome = await box.invoke(
            "rename_village", {"name": f"{player} 001", "reason": "missão: Um nome digno"}
        )
        return outcome.text if outcome.ok else ""

    async def _market(self, box: "Toolbox") -> str:
        ctx = box.ctx
        if ctx.levels.get("market", 0) < 1 or box.dry_run:
            return ""

        stock = {
            "wood": ctx.stock.get("wood", 0),
            "stone": ctx.stock.get("clay", 0),
            "iron": ctx.stock.get("iron", 0),
        }
        high = max(stock, key=stock.get)
        low = min(stock, key=stock.get)
        if stock[high] - stock[low] < 500 or not await self._once(box, "market", 0.5):
            return ""

        offers = await box.actions.market_offers(ctx.game_id)
        choice = self.pick_offer(offers, stock, ctx.village.storage or 0)
        if choice is None:
            return ""

        outcome = await box.invoke(
            "accept_market_offer",
            {
                "receive": choice["receive"],
                "receive_amount": choice["receive_amount"],
                "pay": choice["pay"],
                "amount": choice["pay_amount"],
                "player": choice["player"],
                "reason": f"trocar excedente de {choice['pay']} por {choice['receive']}",
            },
        )
        return outcome.text

    @staticmethod
    def pick_offer(
        offers: list[dict[str, Any]], stock: dict[str, int], storage: int, max_minutes: int = 360
    ) -> dict[str, Any] | None:
        fits = [
            o
            for o in offers
            if o.get("can_accept")
            and o.get("receive")
            and o.get("pay")
            and o["receive"] != o["pay"]
            and o["pay_amount"] <= o["receive_amount"]
            and (o.get("minutes") or 0) <= max_minutes
            and stock[o["pay"]] - o["pay_amount"] >= storage * 0.2
            and stock[o["receive"]] + o["receive_amount"] <= storage
            and stock[o["pay"]] - o["pay_amount"] >= stock[o["receive"]]
        ]
        fits.sort(
            key=lambda o: (
                min(stock, key=stock.get) != o["receive"],
                -o["receive_amount"],
                o.get("minutes") or 0,
            )
        )
        return fits[0] if fits else None
