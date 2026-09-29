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


class ScreenCatalog:
    ACCOUNT: ClassVar[dict[str, tuple[str, dict[str, str]]]] = {
        "profile": ("info_player", {}),
        "awards": ("info_player", {"mode": "awards"}),
        "inventory": ("inventory", {}),
        "daily_bonus": ("daily_bonus", {}),
        "settings": ("settings", {}),
        "flags": ("flags", {}),
    }

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path(settings.html_capture_dir) / "screens"

    def path(self, screen: str) -> Path:
        return self.directory / f"{screen}.html"

    def missing(self, levels: dict[str, int]) -> list[str]:
        buildings = [screen for screen in WATCHED if levels.get(screen, 0) >= 1]
        wanted = ["menu", *buildings, *self.ACCOUNT]
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

        screen, params = self.ACCOUNT.get(name, (name, {}))
        await _open(page, screen, village_id, **params)
        html = await page.evaluate("(document.querySelector('#content_value') || document.body).outerHTML")
        self.save(name, html)
