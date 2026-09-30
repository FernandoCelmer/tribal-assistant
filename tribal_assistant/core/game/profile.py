"""Player profile text (Configurações → Perfil), written once so the quest "A aparência importa" completes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from tribal_assistant.core.game.human import human_click, human_delay
from tribal_assistant.core.game.result import ActionResult
from tribal_assistant.core.game.session import game_session

if TYPE_CHECKING:
    from tribal_assistant.core.game.actions import GameActions

SCREEN = "settings"
TEXT_FIELD = 'form textarea[name="personal_text"], form textarea[name="text"], form textarea'
SUBMIT = 'form input[type="submit"]:visible, form button[type="submit"]:visible, form .btn-confirm-yes:visible, form input.btn:visible'
CURRENT_JS = "() => (document.querySelector('form textarea')?.value || '').trim()"


class Profile:
    def __init__(self, actions: GameActions) -> None:
        self.actions = actions

    async def set_text(self, village_id: str, text: str) -> ActionResult:
        async with game_session.lock:
            page = await self.actions._in_game(village_id, SCREEN)
            await page.wait_for_timeout(800)
            self.actions._capture(await page.content(), "settings_profile")

            field = page.locator(TEXT_FIELD).first
            if not await field.count():
                return ActionResult(False, "set_profile_text", "campo do texto do perfil não encontrado")

            if (await page.evaluate(CURRENT_JS)) == text.strip():
                return ActionResult(True, "set_profile_text", "texto do perfil já está atualizado")

            await field.fill(text)
            await human_delay(500, 1200)

            form = field.locator("xpath=ancestor::form[1]")
            submit = form.locator('input[type="submit"], button[type="submit"], .btn').first
            if not await submit.count():
                submit = page.locator(SUBMIT).first
            if not await submit.count():
                return ActionResult(False, "set_profile_text", "botão de salvar do perfil não encontrado")

            await human_click(page, submit)
            await page.wait_for_timeout(1_500)
            messages = await self.actions.screen_messages(page)
            await self.actions._in_game(village_id, SCREEN)
            saved = (await page.evaluate(CURRENT_JS)) == text.strip()

        if messages["errors"] or not saved:
            return ActionResult(False, "set_profile_text", " | ".join(messages["errors"]) or "o jogo não salvou o texto")

        logger.info("Texto do perfil atualizado")
        return ActionResult(True, "set_profile_text", "texto do perfil salvo", {"notices": messages["notices"]})
