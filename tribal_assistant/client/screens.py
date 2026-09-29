"""Saves the HTML of game screens the first time they exist, so new actions can be mapped."""

from pathlib import Path
from typing import ClassVar

from loguru import logger
from playwright.async_api import Page

from tribal_assistant.core.config import settings

WATCHED = ("smith", "market", "snob", "stable", "garage", "statue")

MENU_JS = """() => {
  const menu = document.querySelector('#topContainer') || document.querySelector('#header_info') || document.body;
  const links = [...menu.querySelectorAll('a[href]')].map(a => `${(a.innerText || a.title || '').trim()} | ${a.getAttribute('href')}`);
  return `<pre>${links.join('\\n')}</pre>\\n${menu.outerHTML}`;
}"""


POPUP_JS = "() => [...document.querySelectorAll('.popup_box_container, .popup_box, #popup_box_knight_recruit')].map(n => n.outerHTML).join('\\n')"


class ScreenCatalog:
    ACCOUNT: ClassVar[dict[str, tuple[str, dict[str, str]]]] = {
        "village_overview": ("overview", {}),
        "daily_bonus": ("info_player", {"mode": "daily_bonus"}),
        "relics": ("relic_system", {}),
        "inventory": ("inventory", {}),
        "flags": ("flags", {}),
        "awards": ("info_player", {"mode": "awards"}),
        "farm_assistant": ("am_farm", {}),
        "profile": ("info_player", {}),
    }

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path(settings.html_capture_dir) / "screens"

    def path(self, screen: str) -> Path:
        return self.directory / f"{screen}.html"

    def missing(self, levels: dict[str, int]) -> list[str]:
        buildings = [screen for screen in WATCHED if levels.get(screen, 0) >= 1]
        popups = ["inventory_details", *(["statue_recruit"] if levels.get("statue", 0) >= 1 else [])]
        wanted = ["menu", *buildings, *self.ACCOUNT, *popups]
        return [screen for screen in wanted if not self.path(screen).exists()]

    def save(self, name: str, html: str, quiet: bool = False) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path(name).write_text(html, encoding="utf-8")

        if not quiet:
            logger.info("Captured the {} screen for mapping ({} bytes)", name, len(html))

    async def capture(self, page: Page, village_id: str, name: str) -> None:
        from tribal_assistant.client.modules.game_sync import _open

        if name == "menu":
            await _open(page, "overview", village_id)
            self.save(name, await page.evaluate(MENU_JS))
            return

        if name == "inventory_details":
            await _open(page, "inventory", village_id)
            await page.wait_for_timeout(2_500)
            parts = []
            for item in await page.locator(".inventory_items .item").all():
                await item.click()
                await page.wait_for_timeout(900)
                parts.append(await page.locator(".inventory_detail").first.evaluate("(n) => n.outerHTML"))
            self.save(name, "\n".join(parts) or "<!-- empty -->")
            return

        if name == "statue_recruit":
            await _open(page, "statue", village_id)
            launch = page.locator(".knight_recruit_launch")
            if await launch.count():
                await launch.first.click()
                await page.wait_for_timeout(1_500)
            self.save(name, await page.evaluate(POPUP_JS) or "<!-- no popup -->")
            await page.keyboard.press("Escape")
            return

        screen, params = self.ACCOUNT.get(name, (name, {}))
        await _open(page, screen, village_id, **params)
        await page.wait_for_timeout(2_500)
        html = await page.evaluate("(document.querySelector('#content_value') || document.body).outerHTML")
        self.save(name, html)
