"""Nobles on the rally point: one attack or a train of attacks confirmed in the same click, barbarians only."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup
from loguru import logger

from tribal_assistant.core.game.human import (
    human_click,
    human_delay,
    human_fill,
    human_type,
    reading_pause,
)
from tribal_assistant.core.game.result import ActionResult
from tribal_assistant.core.game.session import game_session

if TYPE_CHECKING:
    from tribal_assistant.core.game.actions import GameActions

COORDS_RE = re.compile(r"\((\d{1,3}\|\d{1,3})\)")

FILL_TRAIN_ROW_JS = """(units) => {
  const rows = [...document.querySelectorAll('#place_confirm_units tr.units-row')];
  const row = rows[rows.length - 1];
  if (!row) return 0;
  let filled = 0;
  for (const input of row.querySelectorAll('input')) {
    const match = (input.name || '').match(/\\[(\\w+)\\]$/) || [null, input.dataset.unit];
    const unit = match[1];
    if (!unit) continue;
    input.value = String(units[unit] || 0);
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.dispatchEvent(new Event('change', {bubbles: true}));
    if (units[unit]) filled += 1;
  }
  return filled;
}"""

TRAIN_ROWS_JS = "() => document.querySelectorAll('#place_confirm_units tr.units-row').length"


class ConfirmParser:
    """The rally point confirmation: who owns the target and where it is."""

    @staticmethod
    def target(html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        form = soup.select_one("#command-data-form")
        anchor = form.select_one(".village_anchor[data-player]") if form else None
        found = COORDS_RE.search(anchor.get_text(" ", strip=True)) if anchor else None
        x = form.select_one('input[name="x"]') if form else None
        y = form.select_one('input[name="y"]') if form else None
        return {
            "player": str(anchor["data-player"]) if anchor else None,
            "coords": found.group(1) if found else (f"{x['value']}|{y['value']}" if x and y else None),
            "train": bool(soup.select_one("#troop_confirm_train")),
        }

    @classmethod
    def barbarian(cls, html: str, coords: str) -> str | None:
        """Refusal when the confirmation does not show a barbarian at the expected coordinates."""
        found = cls.target(html)
        if found["coords"] != coords:
            return f"confirmação mostra {found['coords']}, esperado {coords}"

        if found["player"] != "0":
            return "o alvo tem dono: nobres só vão para bárbaras"

        return None


class Conquest:
    """Sends one or more noble attacks from one village to one barbarian."""

    def __init__(self, actions: GameActions) -> None:
        self.actions = actions

    async def send_train(self, village_id: str, x: int, y: int, waves: list[dict[str, int]]) -> ActionResult:
        target = f"{x}|{y}"
        if not waves or any(w.get("snob", 0) != 1 for w in waves):
            return ActionResult(False, "send_noble", "cada ataque do trem leva exatamente um nobre")

        async with game_session.lock:
            page = await self.actions._in_game(village_id, "place")
            first = waves[0]
            for unit, count in first.items():
                box = page.locator(f"#unit_input_{unit}")
                if not await box.count():
                    return ActionResult(False, "send_noble", f"sem campo para {unit}")

                await box.first.click()
                await human_type(box.first, str(count), delay=80)

            coords = page.locator("input.target-input-field").first
            if await coords.count() and await coords.is_visible():
                await coords.click()
                await human_type(coords, target, delay=70)
            else:
                await human_fill(page.locator("#inputx"), str(x))
                await human_fill(page.locator("#inputy"), str(y))

            await human_delay(400, 1100)
            await self.actions._click_and_settle(page, page.locator("#target_attack"))
            html = await page.content()
            self.actions._capture(html, "noble-confirm")

            if error := await self.actions._game_error(page):
                return ActionResult(False, "send_noble", error, {"target": target})

            if refusal := ConfirmParser.barbarian(html, target):
                return ActionResult(False, "send_noble", refusal, {"target": target})

            for wave in waves[1:]:
                add = page.locator("#troop_confirm_train")
                if not await add.count():
                    return ActionResult(False, "send_noble", "tela sem trem de ataques", {"target": target})

                await human_click(page, add.first)
                await human_delay(300, 700)
                if not await page.evaluate(FILL_TRAIN_ROW_JS, wave):
                    return ActionResult(False, "send_noble", "não consegui preencher o ataque adicional", {"target": target})

            rows = await page.evaluate(TRAIN_ROWS_JS)
            if len(waves) > 1 and rows != len(waves):
                return ActionResult(False, "send_noble", f"trem com {rows} ataques, esperado {len(waves)}", {"target": target})

            confirm = page.locator("#troop_confirm_submit").first
            if not await confirm.count():
                return ActionResult(False, "send_noble", "botão de envio não encontrado", {"target": target})

            await reading_pause(page)
            await self.actions._click_and_settle(page, confirm)
            if error := await self.actions._game_error(page):
                return ActionResult(False, "send_noble", error, {"target": target})

        logger.info("Nobres enviados de {} para {}: {} ataque(s)", village_id, target, len(waves))
        return ActionResult(True, "send_noble", f"{len(waves)} nobre(s) a caminho de {target}", {"target": target, "waves": waves})
