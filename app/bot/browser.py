"""Playwright browser wrapper with persisted session state."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)


@asynccontextmanager
async def open_browser() -> AsyncIterator[tuple[Page, BrowserContext]]:
    state_file = Path(settings.browser_state_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser: Browser = await playwright.chromium.launch(headless=settings.headless)
        context: BrowserContext = await browser.new_context(
            storage_state=str(state_file) if state_file.exists() else None,
            viewport={"width": 1366, "height": 800},
            user_agent=_USER_AGENT,
            locale="pt-BR",
        )
        page: Page = await context.new_page()
        try:
            yield page, context
        finally:
            await context.storage_state(path=str(state_file))
            logger.info("Session state saved -> {}", state_file)
            await context.close()
            await browser.close()
