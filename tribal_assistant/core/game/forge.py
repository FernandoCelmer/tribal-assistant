"""Crafting event (Bigorna do Rei Mercenário): craft with the free materials and collect the free event pass prizes, never buying anything."""

from __future__ import annotations

from itertools import combinations_with_replacement
from typing import TYPE_CHECKING, Any

from loguru import logger

from tribal_assistant.core.game.human import human_click, human_delay
from tribal_assistant.core.game.result import ActionResult
from tribal_assistant.core.game.session import game_session

if TYPE_CHECKING:
    from tribal_assistant.core.game.actions import GameActions

SCREEN = "event_crafting"
SLOTS = 3

STATE_JS = """() => {
  const materials = Object.fromEntries([...document.querySelectorAll('.material-list li[data-material-id]')].map(li => [
    li.dataset.materialId,
    { amount: Number((li.querySelector('.amount')?.textContent || '0').replace(/\\D/g, '')) || 0, label: (li.dataset.title || '').replace(/^\\d+\\s*/, '') },
  ]));
  const html = document.documentElement.innerHTML;
  const found = html.match(/\\]\\s*,\\s*\\d+\\s*,\\s*(\\{[^{}]*\\})\\s*\\)\\s*;?\\s*\\}\\s*\\)/);
  let recipes = {};
  try { recipes = found ? JSON.parse(found[1]) : {}; } catch (e) { recipes = {}; }
  const badge = document.querySelector('#event_pass_popup_btn .event-pass-badge');
  const prizes = Number((badge?.textContent || '0').replace(/\\D/g, '')) || 0;
  return { active: !!document.querySelector('.material-craft-form'), materials, recipes, prizes };
}"""

COLLECT_ALL = "button.btn-confirm-yes:not([data-cost]):not(.event-pass-buy-btn)"
SELECTED_JS = "() => [...document.querySelectorAll('.material-craft-form input[name=\"material[]\"]')].map(i => i.value).filter(Boolean)"


class Forge:
    def __init__(self, actions: GameActions) -> None:
        self.actions = actions

    @staticmethod
    def pick(amounts: dict[str, int], recipes: dict[str, Any]) -> list[str] | None:
        """Three materials to craft with: a combination not in the formula book first, then a known one."""
        owned = sorted((m for m, n in amounts.items() if n > 0), key=int)
        options = []
        for combo in combinations_with_replacement(owned, SLOTS):
            if all(combo.count(m) <= amounts[m] for m in set(combo)):
                options.append(list(combo))

        if not options:
            return None

        options.sort(key=lambda combo: ("-".join(combo) in recipes, combo))
        return options[0]

    async def state(self, village_id: str) -> dict[str, Any]:
        async with game_session.lock:
            page = await self.actions._in_game(village_id, SCREEN)
            await page.wait_for_timeout(800)
            return await page.evaluate(STATE_JS)

    async def collect_prizes(self, village_id: str) -> ActionResult:
        """Open the event pass and press "Coletar tudo" on the free track; anything with a premium cost is never touched."""
        async with game_session.lock:
            page = await self.actions._in_game(village_id, SCREEN)
            await page.wait_for_timeout(800)
            before = int((await page.evaluate(STATE_JS)).get("prizes", 0))
            if not before:
                return ActionResult(False, "collect_event_prizes", "nenhum prêmio do evento para coletar")

            await human_click(page, page.locator("#event_pass_popup_btn").first)
            await page.wait_for_timeout(2_000)
            button = page.locator(COLLECT_ALL, has_text="Coletar tudo").first
            if not await button.count() or not await button.is_visible():
                return ActionResult(False, "collect_event_prizes", "botão Coletar tudo não encontrado")

            await human_click(page, button)
            await page.wait_for_timeout(2_500)
            messages = await self.actions.screen_messages(page)

            await self.actions._in_game(village_id, SCREEN)
            await page.wait_for_timeout(800)
            after = int((await page.evaluate(STATE_JS)).get("prizes", 0))

        if after >= before:
            return ActionResult(False, "collect_event_prizes", "o jogo não entregou os prêmios" + (f": {' | '.join(messages['errors'])}" if messages["errors"] else ""))

        logger.info("Prêmios do evento coletados: {}", before - after)
        return ActionResult(True, "collect_event_prizes", f"{before - after} prêmio(s) do evento coletado(s)", {"notices": messages["notices"]})

    async def craft(self, village_id: str, materials: list[str]) -> ActionResult:
        async with game_session.lock:
            page = await self.actions._in_game(village_id, SCREEN)
            await page.wait_for_timeout(800)
            before = await page.evaluate(STATE_JS)
            if not before["active"]:
                return ActionResult(False, "craft_event_item", "forja do evento indisponível")

            for material in materials:
                if before["materials"].get(material, {}).get("amount", 0) < materials.count(material):
                    return ActionResult(False, "craft_event_item", f"material {material} insuficiente")

            for material in materials:
                await human_click(page, page.locator(f'.material-list li[data-material-id="{material}"]').first)
                await human_delay(400, 900)

            if sorted(await page.evaluate(SELECTED_JS), key=int) != sorted(materials, key=int):
                return ActionResult(False, "craft_event_item", "a forja não aceitou os materiais escolhidos")

            button = page.locator(".material-craft-form .craft-button:not([disabled])").first
            if not await button.count():
                return ActionResult(False, "craft_event_item", "botão Trabalhe desativado")

            await human_click(page, button)
            await page.wait_for_timeout(3_000)

            messages = await self.actions.screen_messages(page)
            if messages["errors"]:
                return ActionResult(False, "craft_event_item", " | ".join(messages["errors"]))

            await self.actions._in_game(village_id, SCREEN)
            after = await page.evaluate(STATE_JS)

        spent = sum(before["materials"][m]["amount"] - after["materials"].get(m, {}).get("amount", 0) for m in set(materials))
        if spent < SLOTS:
            return ActionResult(False, "craft_event_item", "a forja não consumiu os materiais")

        key = "-".join(sorted(materials, key=int))
        labels = ", ".join(before["materials"][m]["label"] for m in materials)
        new = key not in before["recipes"] and key in after["recipes"]
        logger.info("Forjado com {} ({})", labels, "nova fórmula" if new else key)
        return ActionResult(
            True,
            "craft_event_item",
            f"item trabalhado com {labels}" + (" · fórmula nova" if new else ""),
            {"materials": materials, "formula": key, "new_formula": new, "notices": messages["notices"]},
        )
