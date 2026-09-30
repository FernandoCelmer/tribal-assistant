"""Messages and friends: read the inbox and a conversation, reply, write, accept and ask for friendship."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from tribal_assistant.core.game.human import human_click, human_delay, human_fill
from tribal_assistant.core.game.result import ActionResult
from tribal_assistant.core.game.scraper.social import BuddiesParser, InboxParser
from tribal_assistant.core.game.session import game_session

if TYPE_CHECKING:
    from playwright.async_api import Page

    from tribal_assistant.core.game.actions import GameActions

REPLY_FIELD = 'form[action*="screen=mail"] textarea:visible, textarea[name="text"]:visible'
REPLY_OPEN = '#content_value a:has-text("Responder"), #content_value input[value="Responder"], #content_value button:has-text("Responder")'
SEND_BUTTON = 'input[type="submit"][name="send"], input[type="submit"][value*="Enviar"], button:has-text("Enviar")'
SUBMIT = 'input[type="submit"], button[type="submit"]'
CONFIRM = ".evt-confirm-btn:visible, .btn-confirm-yes:visible"


class Social:
    def __init__(self, actions: GameActions) -> None:
        self.actions = actions

    async def _html(self, village_id: str, screen: str, **params: str) -> tuple[Page, str]:
        page = await self.actions._in_game(village_id, screen, **params)
        return page, await page.content()

    async def inbox(self, village_id: str) -> list[dict[str, Any]]:
        async with game_session.lock:
            _, html = await self._html(village_id, "mail", mode="in")
        return InboxParser.inbox(html)

    async def thread(self, village_id: str, mail_id: str) -> dict[str, Any]:
        async with game_session.lock:
            _, html = await self._html(village_id, "mail", mode="view", view=mail_id)
        self.actions._capture(html, "mail_view")
        return InboxParser.thread(html)

    async def reply(self, village_id: str, mail_id: str, text: str) -> ActionResult:
        async with game_session.lock:
            page, html = await self._html(village_id, "mail", mode="view", view=mail_id)
            before = len(InboxParser.thread(html)["messages"])

            field = page.locator(REPLY_FIELD).first
            if not await field.count():
                opener = page.locator(REPLY_OPEN).first
                if await opener.count():
                    await human_click(page, opener)
                    await page.wait_for_timeout(1_000)
                    self.actions._capture(await page.content(), "mail_reply")
                field = page.locator(REPLY_FIELD).first

            if not await field.count():
                return ActionResult(False, "reply_mail", "campo de resposta não encontrado")

            await human_fill(field, text)
            await human_delay(600, 1500)
            submit = field.locator("xpath=ancestor::form[1]").locator(SUBMIT).first
            if not await submit.count():
                return ActionResult(False, "reply_mail", "botão de enviar a resposta não encontrado")

            await self.actions._click_and_settle(page, submit)
            messages = await self.actions.screen_messages(page)
            _, html = await self._html(village_id, "mail", mode="view", view=mail_id)

        after = InboxParser.thread(html)["messages"]
        sent = len(after) > before or any(text[:40] in m["text"] for m in after)
        if messages["errors"] or not sent:
            return ActionResult(False, "reply_mail", " | ".join(messages["errors"]) or "a resposta não apareceu na conversa")

        logger.info("Mensagem {} respondida", mail_id)
        return ActionResult(True, "reply_mail", "resposta enviada", {"mail_id": mail_id, "notices": messages["notices"]})

    async def send(self, village_id: str, to: str, subject: str, text: str) -> ActionResult:
        async with game_session.lock:
            page, html = await self._html(village_id, "mail", mode="new")
            self.actions._capture(html, "mail_new")

            recipient = page.locator('input[name="to"]').first
            title = page.locator('input[name="subject"]').first
            body = page.locator('textarea[name="text"]').first
            if not (await recipient.count() and await title.count() and await body.count()):
                return ActionResult(False, "send_mail", "formulário de nova mensagem não encontrado")

            await human_fill(recipient, to)
            await human_delay(400, 900)
            await human_fill(title, subject)
            await human_delay(400, 900)
            await human_fill(body, text)
            await human_delay(600, 1500)

            submit = page.locator(SEND_BUTTON).first
            if not await submit.count():
                return ActionResult(False, "send_mail", "botão de enviar não encontrado")

            await self.actions._click_and_settle(page, submit)
            messages = await self.actions.screen_messages(page)
            _, html = await self._html(village_id, "mail", mode="in")

        listed = any(m["subject"].startswith(subject[:30]) for m in InboxParser.inbox(html))
        if messages["errors"] or not listed:
            return ActionResult(False, "send_mail", " | ".join(messages["errors"]) or "a mensagem não apareceu na caixa")

        logger.info("Mensagem enviada a {}", to)
        return ActionResult(True, "send_mail", "mensagem enviada", {"to": to, "notices": messages["notices"]})

    async def buddies(self, village_id: str) -> dict[str, list[dict[str, Any]]]:
        async with game_session.lock:
            _, html = await self._html(village_id, "buddies")
        found = BuddiesParser.parse(html)
        if any(found.values()):
            self.actions._capture(html, "buddies_list")
        return found

    async def accept_buddy(self, village_id: str, buddy_id: str) -> ActionResult:
        async with game_session.lock:
            page, html = await self._html(village_id, "buddies")
            self.actions._capture(html, "buddies_accept")
            link = page.locator(f'a[href*="accept"][href*="{buddy_id}"]').first
            if not await link.count():
                return ActionResult(False, "accept_friend", "pedido de amizade não encontrado")

            await self.actions._click_and_settle(page, link)
            confirm = page.locator(CONFIRM).first
            if await confirm.count():
                await human_click(page, confirm)
                await page.wait_for_timeout(1_200)

            messages = await self.actions.screen_messages(page)
            _, html = await self._html(village_id, "buddies")

        left = BuddiesParser.parse(html)["incoming"]
        if messages["errors"] or any(r.get("id") == buddy_id for r in left):
            return ActionResult(False, "accept_friend", " | ".join(messages["errors"]) or "o pedido continua aberto")

        logger.info("Pedido de amizade {} aceito", buddy_id)
        return ActionResult(True, "accept_friend", "amizade aceita", {"buddy_id": buddy_id, "notices": messages["notices"]})

    async def add_buddy(self, village_id: str, name: str) -> ActionResult:
        async with game_session.lock:
            page, _ = await self._html(village_id, "buddies")
            field = page.locator('form[action*="add_buddy"] input[name="name"]').first
            if not await field.count():
                return ActionResult(False, "add_friend", "formulário de amizade não encontrado")

            await human_fill(field, name)
            await human_delay(500, 1200)
            await field.press("Escape")
            await human_delay(200, 500)
            submit = field.locator("xpath=ancestor::form[1]").locator(SUBMIT).first
            if not await submit.count():
                return ActionResult(False, "add_friend", "botão de adicionar amigo não encontrado")

            before = page.url
            await self.actions._click_and_settle(page, submit)
            if page.url == before and await field.count() and await field.input_value() == name:
                await field.press("Enter")
                await page.wait_for_load_state("load")
            self.actions._capture(await page.content(), "buddies_after_submit")
            messages = await self.actions.screen_messages(page)
            _, html = await self._html(village_id, "buddies")

        self.actions._capture(html, "buddies_added")
        found = BuddiesParser.parse(html)
        listed = any(r["name"].casefold() == name.casefold() for r in found["friends"] + found["outgoing"])
        if messages["errors"] or not (listed or messages["notices"]):
            return ActionResult(False, "add_friend", " | ".join(messages["errors"]) or "o pedido não apareceu na lista")

        logger.info("Pedido de amizade enviado a {}", name)
        return ActionResult(True, "add_friend", "pedido de amizade enviado", {"name": name, "notices": messages["notices"]})
