"""Game actions: the only code that changes game state.

Every action takes the shared browser lock, reaches the screen the way a player
would, acts through the game's own buttons and forms, and reports what the game
answered. Guardrails live one layer up (tribal_assistant.agents.guardrails).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from tribal_assistant.agents.guardrails import SCAVENGE_MIN_POP
from tribal_assistant.agents.knowledge import UNITS
from tribal_assistant.client.human import human_click, human_delay, reading_pause
from tribal_assistant.client.modules.game_sync import (
    BUILD_QUEUE_JS,
    _ensure_in_game,
    _evaluate,
    _open,
)
from tribal_assistant.client.scraper.quests import (
    Quest,
    QuestReward,
    parse_quest_body,
    parse_quest_list,
    parse_rewards,
)
from tribal_assistant.client.screens import ScreenCatalog
from tribal_assistant.client.session import game_session
from tribal_assistant.core.config import settings

UNIT_SCREEN = {
    "spear": "barracks",
    "sword": "barracks",
    "axe": "barracks",
    "archer": "barracks",
    "spy": "stable",
    "light": "stable",
    "marcher": "stable",
    "heavy": "stable",
    "ram": "garage",
    "catapult": "garage",
}

QUEST_POPUP = ".quest-popup-container"

SCAVENGE_HOME_JS = """() => Object.fromEntries([...document.querySelectorAll('.units-entry-all[data-unit]')]
  .map(a => [a.dataset.unit, Number((a.innerText.match(/\\d+/) || [0])[0])]))"""

FREE_FINISH = "#buildqueue .btn-instant-free"
FREE_WAIT_MAX = 75
FREE_WAIT_JS = "(n) => { const at = Number(n.dataset.availableFrom || 0); return at ? Math.max(0, at - Date.now() / 1000) : null; }"

DAILY_CHEST = "#daily_bonus_content .reward:has(.actions a.btn)"
DAILY_STATE_JS = """() => [...document.querySelectorAll('#daily_bonus_content .reward')].map(r => ({
  day: (r.querySelector('.day')?.innerText || '').trim(),
  open: !!r.querySelector('.actions a.btn'),
  item: (r.querySelector('.db-chest')?.dataset.title || '').match(/class="name">([^<]+)/)?.[1] || null,
}))"""

UNLOCK_DIALOG_JS = """(id) => {
  const box = document.querySelector(`#popup_box_unlock-option-${id}`);
  if (!box) return null;
  const num = (sel) => Number((box.querySelector(sel)?.innerText || "0").replace(/\\D/g, ""));
  const res = (window.game_data && game_data.village) || {};
  return {
    wood: num(".wood-value"), stone: num(".stone-value"), iron: num(".iron-value"),
    duration: (box.querySelector(".duration")?.innerText || "").trim(),
    blocked: (box.querySelector(".disabled-explanation")?.innerText || "").trim(),
    have: {wood: Number(res.wood || 0), stone: Number(res.stone || 0), iron: Number(res.iron || 0)},
  };
}"""

SCREEN_MESSAGES_JS = """() => {
  const read = (sel) => [...document.querySelectorAll(sel)]
    .filter(n => n.offsetParent !== null || n.closest('#autoHideBox, .autoHideBox'))
    .map(n => n.innerText.trim()).filter(Boolean);
  const errors = read('.error_box, .autoHideBox.error, #error, .error, .autoHideBox.fail');
  const notices = read('.autoHideBox.success, .autoHideBox.info, .success_box, .info_box.notice, .autoHideBox:not(.error):not(.fail)');
  return {errors: [...new Set(errors)], notices: [...new Set(notices)].filter(t => !errors.includes(t))};
}"""

NEXT_LEVEL_JS = """(id) => {
  const b = window.BuildingMain && BuildingMain.buildings && BuildingMain.buildings[id];
  return b ? Number(b.level_next || 0) : null;
}"""

BUILDING_ERROR_JS = """(id) => {
  const b = window.BuildingMain && BuildingMain.buildings && BuildingMain.buildings[id];
  return b ? (b.error || null) : 'edifício desconhecido';
}"""


@dataclass
class ActionResult:
    ok: bool
    action: str
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


class GameActions:
    """Every state-changing action a player can take, driven through the real game UI."""

    def _capture(self, page_html: str, name: str) -> None:
        """Keep the HTML of screens we act on, so scrapers can be written against real markup."""
        directory = Path(settings.html_capture_dir)
        directory.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        (directory / f"{name}-{stamp}.html").write_text(page_html, encoding="utf-8")

    async def screen_messages(self, page: Page) -> dict[str, list[str]]:
        """Errors and notices the game shows on screen after an action (red boxes, green toasts)."""
        try:
            found = await _evaluate(page, SCREEN_MESSAGES_JS) or {}
        except PlaywrightError:
            return {"errors": [], "notices": []}

        for text in found.get("errors", []):
            logger.warning("Jogo (erro): {}", text)

        for text in found.get("notices", []):
            logger.info("Jogo: {}", text)

        return {"errors": found.get("errors", []), "notices": found.get("notices", [])}

    async def _game_error(self, page: Page) -> str | None:
        messages = await self.screen_messages(page)
        return " | ".join(messages["errors"]) or None

    async def _click_and_settle(self, page: Page, locator: Any, timeout: int = 15_000) -> None:
        """Click a control that may either navigate or update the page over AJAX."""
        try:
            async with page.expect_navigation(wait_until="load", timeout=timeout):
                await human_click(page, locator)
        except PlaywrightError:
            await page.wait_for_load_state("load")

        await human_delay(600, 1500)

    async def _in_game(self, village_id: str, screen: str, **params: str) -> Page:
        page = await game_session.page()
        await _ensure_in_game(page)
        await _open(page, screen, village_id, **params)

        return page

    async def click_free_finish(self, page: Page) -> int:
        """Click the free "finish now" button on short build orders; never the paid premium ones."""
        finished = 0

        for _ in range(5):
            button = page.locator(FREE_FINISH).first
            if not await button.count():
                break

            if not await button.is_visible():
                wait = await button.evaluate(FREE_WAIT_JS)
                if wait is None or wait > FREE_WAIT_MAX:
                    break

                try:
                    await button.wait_for(state="visible", timeout=int(wait * 1000) + 3_000)
                except PlaywrightError:
                    break

            classes = await button.get_attribute("class") or ""
            if "btn-instant-free" not in classes:
                break

            await self._click_and_settle(page, button)
            finished += 1

        if finished:
            logger.info("Finished {} build order(s) for free", finished)
        elif await page.locator("#buildqueue").count():
            html = await page.locator("#buildqueue").first.evaluate("(n) => n.outerHTML")
            ScreenCatalog().save("buildqueue", html, quiet=True)

        return finished

    async def finish_free(self, village_id: str) -> ActionResult:
        """Open the headquarters and use every free "finish now" available."""
        async with game_session.lock:
            page = await self._in_game(village_id, "main")
            finished = await self.click_free_finish(page)

        if not finished:
            return ActionResult(
                False, "finish_free", "nenhuma construção com conclusão grátis agora"
            )

        return ActionResult(
            True,
            "finish_free",
            f"{finished} construção(ões) concluída(s) grátis",
            {"finished": finished},
        )

    async def unlock_scavenge(self, village_id: str, option_id: int) -> ActionResult:
        """Unlock a scavenging tier from the rally point, after checking its cost against the stock."""
        async with game_session.lock:
            page = await self._in_game(village_id, "place", mode="scavenge")

            option = page.locator(".options-container .scavenge-option").nth(option_id - 1)
            button = option.locator(".unlock-button")
            if not await button.count() or not await button.first.is_visible():
                return ActionResult(
                    False,
                    "unlock_scavenge",
                    f"coleta {option_id} não está disponível para desbloquear",
                )

            await button.first.scroll_into_view_if_needed()
            await human_delay(300, 900)
            await button.first.click()

            try:
                await page.locator(f"#popup_box_unlock-option-{option_id}").wait_for(
                    state="visible", timeout=8_000
                )
            except PlaywrightError:
                return ActionResult(False, "unlock_scavenge", "janela de desbloqueio não abriu")

            info = await page.evaluate(UNLOCK_DIALOG_JS, option_id)
            if info is None:
                return ActionResult(False, "unlock_scavenge", "janela de desbloqueio não abriu")

            cost = {"wood": info["wood"], "clay": info["stone"], "iron": info["iron"]}
            if info["blocked"]:
                await self._close_popup(page)
                return ActionResult(False, "unlock_scavenge", info["blocked"], {"cost": cost})

            short = [
                k
                for k, v in (
                    ("wood", info["wood"]),
                    ("stone", info["stone"]),
                    ("iron", info["iron"]),
                )
                if v > info["have"][k]
            ]
            if short:
                await self._close_popup(page)
                return ActionResult(
                    False,
                    "unlock_scavenge",
                    "recursos insuficientes: " + ", ".join(short),
                    {"cost": cost},
                )

            confirm = page.locator(
                f"#popup_box_unlock-option-{option_id} .scavenge-option-unlock-dialog a.btn"
            ).first
            await human_delay(600, 1500)
            await confirm.click()
            await page.wait_for_timeout(2_000)

            if error := await self._game_error(page):
                return ActionResult(False, "unlock_scavenge", error, {"cost": cost})

            logger.info(
                "Unlocking scavenging option {} in village {} for {}", option_id, village_id, cost
            )
            return ActionResult(
                True,
                "unlock_scavenge",
                f"coleta {option_id} desbloqueando ({info['duration']})",
                {"option_id": option_id, "cost": cost, "duration": info["duration"]},
            )

    async def send_scavenge(
        self, village_id: str, option_id: int, units: dict[str, int]
    ) -> ActionResult:
        """Send troops scavenging on one tier with the free start button (never the premium +20%)."""
        units = {u: n for u, n in units.items() if n > 0}
        if not units:
            return ActionResult(False, "send_scavenge", "nenhuma tropa informada")

        async with game_session.lock:
            page = await self._in_game(village_id, "place", mode="scavenge")

            option = page.locator(".options-container .scavenge-option").nth(option_id - 1)
            start = option.locator(".free_send_button")
            if not await start.count() or not await start.first.is_visible():
                return ActionResult(
                    False, "send_scavenge", f"coleta {option_id} não está livre para enviar"
                )

            home = await page.evaluate(SCAVENGE_HOME_JS) or {}
            units = {
                u: min(n, int(home.get(u, 0))) for u, n in units.items() if int(home.get(u, 0)) > 0
            }
            pop = sum(UNITS[u].pop * n for u, n in units.items() if u in UNITS)
            if pop < SCAVENGE_MIN_POP:
                return ActionResult(
                    False,
                    "send_scavenge",
                    f"só {pop} de população disponível em casa; a coleta exige {SCAVENGE_MIN_POP}",
                    {"home": home},
                )

            for unit, count in units.items():
                field_ = page.locator(f"input.unitsInput[name='{unit}']").first
                if not await field_.count():
                    return ActionResult(False, "send_scavenge", f"{unit} não pode coletar")

                await field_.click()
                await field_.fill("")
                await field_.type(str(count), delay=80)

            await human_delay(500, 1200)
            await start.first.click()
            await page.wait_for_timeout(2_000)

            if error := await self._game_error(page):
                return ActionResult(
                    False, "send_scavenge", error, {"option_id": option_id, "units": units}
                )

            logger.info("Scavenging option {} in village {} with {}", option_id, village_id, units)
            return ActionResult(
                True,
                "send_scavenge",
                f"{sum(units.values())} tropa(s) coletando no nível {option_id}",
                {"option_id": option_id, "units": units},
            )

    async def upgrade_building(
        self, village_id: str, building: str, finish_free: bool = True
    ) -> ActionResult:
        """Queue the next level of `building` from the headquarters screen."""
        async with game_session.lock:
            page = await self._in_game(village_id, "main")
            before = await _evaluate(page, BUILD_QUEUE_JS) or []
            next_before = await page.evaluate(NEXT_LEVEL_JS, building)

            button = page.locator(f'a.btn-build:not(.btn-bcr)[data-building="{building}"]')
            if not await button.count() or not await button.first.is_visible():
                reason = await page.evaluate(BUILDING_ERROR_JS, building)
                return ActionResult(
                    False,
                    "upgrade_building",
                    reason or "sem botão de construção",
                    {"building": building},
                )

            level = await button.first.get_attribute("data-level-next")
            await self._click_and_settle(page, button.first)

            if error := await self._game_error(page):
                return ActionResult(False, "upgrade_building", error, {"building": building})

            if not await page.locator("#buildqueue").count():
                await _open(page, "main", village_id)

            after = await _evaluate(page, BUILD_QUEUE_JS) or []
            next_after = await page.evaluate(NEXT_LEVEL_JS, building)
            finished = (
                next_before is not None and next_after is not None and next_after > next_before
            )

            if len(after) <= len(before) and not finished:
                self._capture(await page.content(), f"main-upgrade-{building}")
                return ActionResult(
                    False,
                    "upgrade_building",
                    "fila de construção não mudou",
                    {"building": building},
                )

            finished = await self.click_free_finish(page) if finish_free else 0

            logger.info("Queued {} level {} in village {}", building, level, village_id)
            return ActionResult(
                True,
                "upgrade_building",
                f"{building} → nível {level} na fila",
                {"building": building, "level": level, "queue": after, "finished_free": finished},
            )

    async def recruit(self, village_id: str, unit: str, count: int) -> ActionResult:
        """Recruit `count` units of `unit` in the building that trains it."""
        screen = UNIT_SCREEN.get(unit)
        if screen is None or count <= 0:
            return ActionResult(
                False, "recruit", f"unidade {unit!r} não recrutável aqui", {"unit": unit}
            )

        async with game_session.lock:
            page = await self._in_game(village_id, screen)

            field_ = page.locator(f"#train_form input[name='{unit}']")
            if not await field_.count() or not await field_.first.is_visible():
                return ActionResult(
                    False, "recruit", f"{unit} indisponível em {screen}", {"unit": unit}
                )

            available = page.locator(f"#{unit}_0_a")
            if await available.count():
                text = (await available.first.inner_text()).strip("() \n")
                if text.isdigit() and int(text) < count:
                    count = int(text)

            if count <= 0:
                return ActionResult(False, "recruit", "sem recursos ou população", {"unit": unit})

            await field_.first.click()
            await field_.first.type(str(count), delay=90)
            await self._click_and_settle(page, page.locator("#train_form .btn-recruit").first)

            if error := await self._game_error(page):
                return ActionResult(False, "recruit", error, {"unit": unit, "count": count})

            logger.info("Recruiting {} {} in village {}", count, unit, village_id)
            return ActionResult(
                True, "recruit", f"{count} {unit} em recrutamento", {"unit": unit, "count": count}
            )

    async def send_attack(
        self, village_id: str, x: int, y: int, units: dict[str, int]
    ) -> ActionResult:
        """Send an attack from the rally point: fill troops and target, confirm."""
        units = {u: n for u, n in units.items() if n > 0}
        if not units:
            return ActionResult(False, "send_attack", "nenhuma tropa informada")

        target = f"{x}|{y}"

        async with game_session.lock:
            page = await self._in_game(village_id, "place")

            for unit, count in units.items():
                box = page.locator(f"#unit_input_{unit}")
                if not await box.count():
                    return ActionResult(
                        False, "send_attack", f"sem campo para {unit}", {"unit": unit}
                    )

                home = await box.first.get_attribute("data-all-count")
                if home is not None and int(home) < count:
                    return ActionResult(
                        False, "send_attack", f"só há {home} {unit} na aldeia", {"unit": unit}
                    )

                await box.first.click()
                await box.first.type(str(count), delay=80)

            coords = page.locator("input.target-input-field").first
            if await coords.count() and await coords.is_visible():
                await coords.click()
                await coords.type(target, delay=70)
            else:
                await page.locator("#inputx").fill(str(x))
                await page.locator("#inputy").fill(str(y))

            await human_delay(400, 1100)
            await self._click_and_settle(page, page.locator("#target_attack"))
            self._capture(await page.content(), "place-confirm")

            if error := await self._game_error(page):
                return ActionResult(False, "send_attack", error, {"target": target})

            confirm = page.locator(
                "#troop_confirm_submit, #troop_confirm_go, #command-data-form .btn-attack"
            ).first
            if not await confirm.count():
                return ActionResult(
                    False, "send_attack", "tela de confirmação não encontrada", {"target": target}
                )

            arrival = None
            for selector in ("#date_arrival", ".relative_time"):
                node = page.locator(selector)
                if await node.count():
                    arrival = (await node.first.inner_text()).strip()
                    break

            await reading_pause(page)
            await self._click_and_settle(page, confirm)

            if error := await self._game_error(page):
                return ActionResult(False, "send_attack", error, {"target": target})

            logger.info("Attack sent from {} to {} with {}", village_id, target, units)
            return ActionResult(
                True,
                "send_attack",
                f"ataque enviado para {target}",
                {"target": target, "units": units, "arrival": arrival},
            )

    async def _open_quests(self, page: Page) -> bool:
        popup = page.locator(QUEST_POPUP)
        if await popup.count() and await popup.first.is_visible():
            return True

        trigger = page.locator("#new_quest, .quest[data-id], #questlog_new .quest").first
        if not await trigger.count():
            return False

        await human_click(page, trigger)

        try:
            await popup.first.wait_for(state="visible", timeout=10_000)
        except PlaywrightError:
            return False

        await human_delay(500, 1200)
        return True

    async def _close_popup(self, page: Page) -> None:
        close = page.locator(".popup_box_close").first

        if await close.count() and await close.is_visible():
            await human_click(page, close)
        else:
            await page.keyboard.press("Escape")

    async def _popup_html(self, page: Page) -> str:
        return await page.locator(QUEST_POPUP).first.evaluate("n => n.outerHTML")

    async def _select_quest(self, page: Page, quest_id: str) -> bool:
        """Show a quest in the popup, expanding its quest line first (popup UI only, no game action)."""
        link = page.locator(f'{QUEST_POPUP} a.quest-link[data-quest-id="{quest_id}"]').first
        if not await link.count():
            return False

        if not await link.is_visible():
            line = await link.get_attribute("data-questline-id")
            header = page.locator(f"{QUEST_POPUP} #questline-header-{line}").first
            if await header.count():
                await header.evaluate("n => n.click()")
                await page.wait_for_timeout(400)

        await link.evaluate("n => n.click()")
        await page.wait_for_timeout(700)
        return True

    async def read_quests(self, village_id: str) -> tuple[list[Quest], list[QuestReward]]:
        """Open the quest popup and read every quest line plus claimable rewards."""
        async with game_session.lock:
            page = await self._in_game(village_id, "overview")
            if not await self._open_quests(page):
                return [], []

            quests = parse_quest_list(await self._popup_html(page))

            for quest in quests:
                if not await self._select_quest(page, quest.quest_id):
                    continue
                quest.description, quest.goals, quest.can_complete = parse_quest_body(
                    await self._popup_html(page)
                )

            rewards = parse_rewards(await self._popup_html(page))
            await self._close_popup(page)

            return quests, rewards

    async def complete_quest(self, village_id: str, quest_id: str) -> ActionResult:
        """Press "Missão completa" on a finished quest."""
        async with game_session.lock:
            page = await self._in_game(village_id, "overview")
            if not await self._open_quests(page):
                return ActionResult(False, "complete_quest", "missões indisponíveis")

            if not await self._select_quest(page, quest_id):
                await self._close_popup(page)
                return ActionResult(False, "complete_quest", f"missão {quest_id} não encontrada")

            button = page.locator(f"{QUEST_POPUP} #main-tab .status-btn:not(.hidden)").first
            if not await button.count():
                await self._close_popup(page)
                return ActionResult(
                    False, "complete_quest", "missão ainda não concluída", {"quest_id": quest_id}
                )

            await human_click(page, button)
            await human_delay(900, 1800)
            await self._close_popup(page)

            logger.info("Completed quest {}", quest_id)
            return ActionResult(
                True, "complete_quest", f"missão {quest_id} concluída", {"quest_id": quest_id}
            )

    async def open_daily_bonus(self, village_id: str) -> ActionResult:
        """Open every unlocked daily bonus chest in the profile; items go to the inventory."""
        async with game_session.lock:
            page = await self._in_game(village_id, "info_player", mode="daily_bonus")
            chests = await page.evaluate(DAILY_STATE_JS) or []

            opened = 0
            for _ in range(10):
                reward = page.locator(DAILY_CHEST).first
                if not await reward.count():
                    break

                await reward.locator(".chest_container").first.hover()
                await human_delay(300, 700)

                button = reward.locator(".actions a.btn").first
                if await button.is_visible():
                    await human_click(page, button)
                else:
                    await button.evaluate("(n) => n.click()")

                await human_delay(900, 1800)

                if not opened:
                    self._capture(await page.content(), "daily-bonus-opened")

                opened += 1
                await self._close_popup(page)
                await human_delay(400, 900)

        if not opened:
            return ActionResult(
                False, "open_daily_bonus", "nenhum baú diário para abrir", {"chests": chests}
            )

        items = [c["item"] for c in chests if c.get("open") and c.get("item")][:opened]
        logger.info("Opened {} daily bonus chest(s)", opened)
        return ActionResult(
            True,
            "open_daily_bonus",
            f"{opened} baú(s) diário(s) aberto(s): {', '.join(items) or 'itens no inventário'}",
            {"opened": opened, "items": items},
        )

    async def recruit_knight(self, village_id: str) -> ActionResult:
        """Recruit a paladin at the statue with resources (never premium points)."""
        async with game_session.lock:
            page = await self._in_game(village_id, "statue")

            launch = page.locator(".knight_recruit_launch")
            if not await launch.count() or not await launch.first.is_visible():
                return ActionResult(
                    False, "recruit_knight", "sem opção de recrutar paladino nesta aldeia"
                )

            await human_click(page, launch.first)
            await human_delay(700, 1400)

            confirm = page.locator("#knight_recruit_confirm")
            if not await confirm.count():
                self._capture(await page.content(), "statue-recruit")
                return ActionResult(False, "recruit_knight", "janela de recrutamento não abriu")

            await human_click(page, confirm.first)
            await page.wait_for_timeout(2_000)

            messages = await self.screen_messages(page)
            if messages["errors"]:
                return ActionResult(False, "recruit_knight", " | ".join(messages["errors"]))

        logger.info("Recruiting a paladin in village {}", village_id)
        return ActionResult(
            True, "recruit_knight", "paladino em recrutamento", {"notices": messages["notices"]}
        )

    async def inventory(self, village_id: str) -> list[dict[str, Any]]:
        """Items in the inventory with their detail text and whether they can be used."""
        async with game_session.lock:
            page = await self._in_game(village_id, "inventory")
            await page.wait_for_timeout(2_000)

            items = []
            for item in await page.locator(".inventory_items .item").all():
                key = (await item.get_attribute("id") or "").removeprefix("item_")
                await item.click()
                await page.wait_for_timeout(700)
                detail = page.locator(".inventory_detail").first
                items.append(
                    {
                        "key": key,
                        "name": await item.get_attribute("data-title"),
                        "detail": " ".join((await detail.inner_text()).split()),
                        "usable": await detail.locator(".detail_actions a.btn").count() > 0,
                    }
                )

        return items

    async def use_item(self, village_id: str, key: str) -> ActionResult:
        """Use one inventory item (resource pack, construction bonus...) through its Usar button."""
        async with game_session.lock:
            page = await self._in_game(village_id, "inventory")
            await page.wait_for_timeout(2_000)

            item = page.locator(f"#item_{key}")
            if not await item.count():
                return ActionResult(False, "use_item", f"item {key} não está no inventário")

            name = await item.first.get_attribute("data-title")
            await human_click(page, item.first)
            await human_delay(600, 1200)

            use = page.locator(".inventory_detail .detail_actions a.btn").first
            if not await use.count():
                return ActionResult(False, "use_item", f"{name} não pode ser usado agora")

            await human_click(page, use)
            await human_delay(900, 1600)

            dialog = page.locator(
                ".popup_box_container .btn-confirm-yes, .popup_box_container a.btn:visible, .popup_box_container input.btn:visible"
            )
            if await dialog.count():
                self._capture(await page.content(), f"use-item-{key}")
                await human_click(page, dialog.first)
                await page.wait_for_timeout(1_500)

            messages = await self.screen_messages(page)
            if messages["errors"]:
                return ActionResult(
                    False, "use_item", " | ".join(messages["errors"]), {"item": name}
                )

        logger.info("Used item {} ({}) in village {}", key, name, village_id)
        return ActionResult(
            True, "use_item", f"{name} usado", {"item": name, "notices": messages["notices"]}
        )

    async def choose_relic(self, village_id: str, index: int) -> ActionResult:
        """Pick one of the starter relics offered in the treasury (relic_system)."""
        async with game_session.lock:
            page = await self._in_game(village_id, "relic_system")

            link = page.locator(f'a.btn[href*="mode=choose_relic"][href*="index={index}"]')
            if not await link.count():
                self._capture(await page.content(), "relic-missing")
                return ActionResult(
                    False,
                    "choose_relic",
                    "nenhuma relíquia inicial para escolher",
                    {"url": page.url},
                )

            await self._click_and_settle(page, link.first)
            await human_delay(700, 1400)

            confirm = page.locator(
                ".popup_box_container .btn-confirm-yes, .popup_box_container a.btn:visible"
            )
            if await confirm.count():
                await human_click(page, confirm.first)
                await page.wait_for_timeout(1_500)

            self._capture(await page.content(), "relic-chosen")
            messages = await self.screen_messages(page)
            if messages["errors"]:
                return ActionResult(False, "choose_relic", " | ".join(messages["errors"]))

        logger.info("Chose starter relic {} in village {}", index, village_id)
        return ActionResult(
            True, "choose_relic", f"relíquia {index} escolhida", {"notices": messages["notices"]}
        )

    async def _open_relics(self, page: Page, village_id: str) -> None:
        await _open(page, "relic_system", village_id)
        await page.wait_for_timeout(1_500)

    async def equip_relic(self, village_id: str) -> ActionResult:
        """Equip the first relic from the treasury into this village's free relic slot."""
        async with game_session.lock:
            page = await self._in_game(village_id, "relic_system")
            await page.wait_for_timeout(2_000)

            relic = page.locator("#relics img[data-id]").first
            if not await relic.count():
                return ActionResult(
                    False, "equip_relic", "nenhuma relíquia no inventário da tesouraria"
                )

            relic_id = await relic.get_attribute("data-id")
            await human_click(page, relic)
            await human_delay(800, 1500)

            equip = page.locator("#equip_button:visible")
            if not await equip.count():
                self._capture(await page.content(), "relic-equip-missing")
                return ActionResult(
                    False, "equip_relic", "botão de equipar não encontrado", {"relic": relic_id}
                )

            await human_click(page, equip.first)
            await human_delay(900, 1600)

            confirm = page.locator(".evt-confirm-btn:visible, .btn-confirm-yes:visible")
            if await confirm.count():
                await human_click(page, confirm.first)
                await page.wait_for_timeout(1_500)

            messages = await self.screen_messages(page)
            self._capture(await page.content(), "relic-equip")
            if messages["errors"]:
                return ActionResult(
                    False, "equip_relic", " | ".join(messages["errors"]), {"relic": relic_id}
                )

            await self._open_relics(page, village_id)
            status = " ".join((await page.locator("#village_equip_status").inner_text()).split())
            if "nenhuma relíquia equipada" in status:
                return ActionResult(
                    False,
                    "equip_relic",
                    f"relíquia não ficou equipada: {status}",
                    {"relic": relic_id},
                )

        logger.info("Equipped relic {} in village {}", relic_id, village_id)
        return ActionResult(
            True,
            "equip_relic",
            f"relíquia {relic_id} equipada",
            {"relic": relic_id, "notices": messages["notices"]},
        )

    async def rename_village(self, village_id: str, name: str) -> ActionResult:
        """Rename the village from the headquarters form."""
        async with game_session.lock:
            page = await self._in_game(village_id, "main")

            field_ = page.locator('form[action*="action=change_name"] input[name="name"]').first
            if not await field_.count():
                return ActionResult(False, "rename_village", "formulário de nome não encontrado")

            await field_.click()
            await field_.fill("")
            await field_.type(name[:32], delay=70)
            await human_delay(400, 900)
            await self._click_and_settle(
                page, page.locator('form[action*="action=change_name"] input[type="submit"]').first
            )

            messages = await self.screen_messages(page)
            if messages["errors"]:
                return ActionResult(False, "rename_village", " | ".join(messages["errors"]))

        logger.info("Renamed village {} to {}", village_id, name)
        return ActionResult(
            True,
            "rename_village",
            f"aldeia renomeada para {name}",
            {"notices": messages["notices"]},
        )

    async def assign_flag(self, village_id: str, flag_type: int, level: int) -> ActionResult:
        """Assign an owned flag (type and level from the flags screen) to this village."""
        async with game_session.lock:
            page = await self._in_game(village_id, "flags")

            box = page.locator(f"#flag_box_{flag_type}_{level}:not(.flag_box_empty)")
            if not await box.count():
                return ActionResult(
                    False, "assign_flag", f"bandeira {flag_type}_{level} não disponível"
                )

            title = await box.first.get_attribute("data-title")
            await human_click(page, box.first)
            await human_delay(800, 1500)

            confirm = page.locator(
                ".evt-confirm-btn:visible, .btn-confirm-yes:visible, .popup_box_container a.btn:visible"
            )
            if await confirm.count():
                self._capture(await page.content(), "flag-assign")
                await human_click(page, confirm.first)
                await page.wait_for_timeout(1_500)

            messages = await self.screen_messages(page)
            if messages["errors"]:
                return ActionResult(False, "assign_flag", " | ".join(messages["errors"]))

            await _open(page, "flags", village_id)
            current = " ".join((await page.locator("#content_value").inner_text()).split())

        if title and title.split(" ")[0] not in current:
            return ActionResult(False, "assign_flag", f"bandeira não ficou atribuída ({title})")

        logger.info("Assigned flag {}_{} in village {}", flag_type, level, village_id)
        return ActionResult(
            True, "assign_flag", f"bandeira atribuída: {title}", {"notices": messages["notices"]}
        )

    async def claim_rewards(self, village_id: str) -> ActionResult:
        """Claim every reward waiting in the "Recompensas" tab (resources land in this village)."""
        async with game_session.lock:
            page = await self._in_game(village_id, "overview")
            if not await self._open_quests(page):
                return ActionResult(False, "claim_rewards", "missões indisponíveis")

            tab = page.locator(f'{QUEST_POPUP} a.tab-link[data-tab="reward-tab"]').first
            if await tab.count():
                await human_click(page, tab)
                await page.wait_for_timeout(700)

            claimed = []
            for _ in range(20):
                button = page.locator(
                    f"{QUEST_POPUP} #reward-tab .reward-system-claim-button:visible"
                ).first
                if not await button.count():
                    break

                claimed.append(await button.get_attribute("data-reward-id"))
                await human_click(page, button)
                await human_delay(700, 1500)

            await self._close_popup(page)

            if not claimed:
                return ActionResult(False, "claim_rewards", "nenhuma recompensa disponível")

            logger.info("Claimed {} reward(s)", len(claimed))
            return ActionResult(
                True,
                "claim_rewards",
                f"{len(claimed)} recompensa(s) coletada(s)",
                {"rewards": claimed},
            )
