"""Farm assistant (am_farm): read its state, save templates A and B, and send a raid with one click on a row.

Never activates or extends the premium feature: when the screen is not there, it reports unavailable and stops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from tribal_assistant.core.game.human import human_click, human_delay
from tribal_assistant.core.game.result import ActionResult
from tribal_assistant.core.game.scraper.farm_assistant import TEMPLATES, FarmAssistantParser
from tribal_assistant.core.game.session import game_session

if TYPE_CHECKING:
    from tribal_assistant.core.game.actions import GameActions

SCREEN = "am_farm"
FORM = 'form[action*="action=edit_all"]'

ROW_STATE_JS = """(id) => {
  const row = document.querySelector('#plunder_list tr#village_' + id);
  const home = Object.fromEntries([...document.querySelectorAll('#units_home td.unit-item[data-unit-count]')]
    .map(td => [td.id || '', Number(td.dataset.unitCount || 0)]));
  if (!row) return {present: false, visible: false, disabled: [], home};
  const style = getComputedStyle(row);
  const visible = !!row.offsetParent && style.display !== 'none' && style.visibility !== 'hidden';
  const disabled = ['a', 'b', 'c'].filter(k => {
    const a = row.querySelector('a.farm_icon_' + k);
    return !a || a.classList.contains('farm_icon_disabled') || a.classList.contains('done');
  });
  return {present: true, visible, disabled, home};
}"""


class FarmAssistant:
    def __init__(self, actions: GameActions) -> None:
        self.actions = actions

    async def _open(self, village_id: str) -> tuple[Any, dict[str, Any]]:
        page = await self.actions._in_game(village_id, SCREEN)
        html = await page.content()
        state = FarmAssistantParser.parse(html)
        if f"screen={SCREEN}" not in page.url:
            state["available"] = False
            state["reason"] = f"tela redirecionou para {page.url.split('?')[-1][:80]}"

        if not state["available"]:
            self.actions._capture(html, "am-farm-unavailable")

        return page, state

    async def state(self, village_id: str) -> dict[str, Any]:
        async with game_session.lock:
            _, state = await self._open(village_id)
            return state

    async def set_templates(self, village_id: str, wanted: dict[str, dict[str, int]]) -> ActionResult:
        """Fill the template fields (every unit not asked goes to zero), save, and read back what the game stored."""
        async with game_session.lock:
            page, state = await self._open(village_id)
            if not state["available"]:
                return ActionResult(False, "set_farm_templates", f"assistente de saque indisponível: {state['reason']}")

            form = page.locator(FORM).first
            if not await form.count():
                return ActionResult(False, "set_farm_templates", "formulário dos modelos não encontrado")

            for letter, units in wanted.items():
                fields = (state["templates"].get(letter) or {}).get("units") or {}
                missing = [u for u, n in units.items() if n > 0 and u not in fields]
                if letter not in TEMPLATES or missing:
                    return ActionResult(False, "set_farm_templates", f"modelo {letter.upper()} sem campo para {', '.join(missing) or letter}")

                for unit in fields:
                    box = form.locator(f'input[name="{unit}[{TEMPLATES[letter]}]"]')
                    if await box.count():
                        await box.first.fill(str(int(units.get(unit, 0))))
                        await human_delay(120, 300)

            await human_delay(400, 900)
            await self.actions._click_and_settle(page, form.locator('input[type="submit"]').first)
            self.actions._capture(await page.content(), "am-farm-templates")

            messages = await self.actions.screen_messages(page)
            if messages["errors"]:
                return ActionResult(False, "set_farm_templates", " | ".join(messages["errors"]))

            _, saved = await self._open(village_id)

        stored = {letter: FarmAssistantParser.squad(saved, letter) for letter in wanted}
        asked = {letter: {u: n for u, n in units.items() if n > 0} for letter, units in wanted.items()}
        if stored != asked:
            return ActionResult(False, "set_farm_templates", f"o jogo guardou {stored}, pedido {asked}", {"stored": stored})

        logger.info("Modelos do assistente de saque salvos na aldeia {}: {}", village_id, stored)
        text = "; ".join(f"{k.upper()} = {v or 'vazio'}" for k, v in stored.items())
        return ActionResult(True, "set_farm_templates", f"modelos salvos: {text}", {"templates": stored, "notices": messages["notices"]})

    async def send(self, village_id: str, target_id: int, coords: str, letter: str, units: dict[str, int]) -> ActionResult:
        """Click A or B on the row of this barbarian, after checking the row, the template and the troops at home."""
        action = "send_farm_template"
        async with game_session.lock:
            page, state = await self._open(village_id)
            if not state["available"]:
                return ActionResult(False, action, f"assistente de saque indisponível: {state['reason']}")

            row = next((r for r in state["targets"] if r["village_id"] == int(target_id)), None)
            if row is None:
                return ActionResult(False, action, f"{coords} não está na lista do assistente de saque")

            if row["coords"] != coords:
                return ActionResult(False, action, f"linha {target_id} é {row['coords']}, não {coords}")

            current = FarmAssistantParser.squad(state, letter)
            if current != {u: n for u, n in units.items() if n > 0}:
                return ActionResult(False, action, f"modelo {letter.upper()} no jogo é {current or 'vazio'}, esperado {units}")

            if not row["buttons"].get(letter):
                return ActionResult(False, action, f"botão {letter.upper()} desabilitado na linha de {coords}")

            short = [u for u, n in current.items() if state["home"].get(u, 0) < n]
            if short:
                return ActionResult(False, action, f"tropas insuficientes em casa para o modelo {letter.upper()}: {', '.join(short)}")

            before = state["home"]
            await reading_row(page, target_id)
            await human_click(page, page.locator(f"#plunder_list tr#village_{target_id} a.farm_icon_{letter}").first)
            await human_delay(1200, 2200)
            self.actions._capture(await page.content(), f"am-farm-send-{letter}")

            messages = await self.actions.screen_messages(page)
            if messages["errors"]:
                return ActionResult(False, action, " | ".join(messages["errors"]), {"target": coords})

            after = await page.evaluate(ROW_STATE_JS, int(target_id))

        left = after.get("home") or {}
        spent = any(left.get(u, before.get(u, 0)) < before.get(u, 0) for u in current)
        gone = not after.get("present") or not after.get("visible") or letter in (after.get("disabled") or [])
        if not (spent or gone or messages["notices"]):
            return ActionResult(False, action, f"sem confirmação do envio para {coords}", {"target": coords})

        logger.info("Saque {} enviado pelo assistente de {} para {}", letter.upper(), village_id, coords)
        return ActionResult(
            True,
            action,
            f"saque modelo {letter.upper()} enviado para {coords}",
            {"target": coords, "units": current, "template": letter, "notices": messages["notices"]},
        )


async def reading_row(page: Any, target_id: int) -> None:
    row = page.locator(f"#plunder_list tr#village_{target_id}").first
    if await row.count():
        await row.scroll_into_view_if_needed()
        await human_delay(300, 800)
