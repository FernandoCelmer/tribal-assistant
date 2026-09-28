"""Login + world select."""

from loguru import logger
from playwright.async_api import Page

from app.bot.human import human_delay
from app.core.config import settings

LOGIN_URL = "https://www.tribalwars.com.br/"


async def login(page: Page) -> None:
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await human_delay()

    if await page.locator("#user").count():
        logger.info("Filling credentials")
        await page.fill("#user", settings.tw_username)
        await human_delay(400, 900)
        await page.fill("#password", settings.tw_password)
        await human_delay(400, 900)
        await page.click("a.btn-login")
        await page.wait_for_load_state("networkidle")
    else:
        logger.info("Session already active, skipping login form")

    await human_delay()
    await _enter_world(page)


async def _enter_world(page: Page) -> None:
    server = settings.tw_server
    selector = f"a.world_button_active[data-world-id*='{server}'], span:has-text('{server}')"
    if await page.locator(selector).count():
        logger.info("Entering world {}", server)
        await page.locator(selector).first.click()
        await page.wait_for_load_state("networkidle")
    else:
        logger.warning("World selector not found — assuming already inside world")
