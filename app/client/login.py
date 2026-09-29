"""Login + world select."""

from loguru import logger
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.client.human import human_delay
from app.core.config import settings
from app.core.errors import UpstreamError

LOGIN_URL = "https://www.tribalwars.com.br/"
PLAY_URL = LOGIN_URL + "page/play/{server}"

LOGIN_FORM_SELECTOR = "#login_form #user"
VILLAGE_MENU_SELECTOR = "#menu_row2_village"

LOGIN_TIMEOUT_MS = 120_000
WORLD_TIMEOUT_MS = 30_000


async def login(page: Page) -> None:
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await human_delay()

    if await page.locator(LOGIN_FORM_SELECTOR).count():
        await _submit_credentials(page)
    else:
        logger.info("Session already active, skipping login form")

    await human_delay()
    await _enter_world(page)


async def _submit_credentials(page: Page) -> None:
    logger.info("Filling credentials")
    await page.fill("#user", settings.tw_username)
    await human_delay(400, 900)
    await page.fill("#password", settings.tw_password)
    await human_delay(400, 900)
    await page.click("a.btn-login")

    logger.info("Waiting for captcha/login (up to {}s)", LOGIN_TIMEOUT_MS // 1000)
    try:
        await page.wait_for_selector(LOGIN_FORM_SELECTOR, state="detached", timeout=LOGIN_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise UpstreamError(
            "Login não concluiu em 2 min: captcha não resolvido ou usuário/senha inválidos"
        ) from exc
    await page.wait_for_load_state("domcontentloaded")


async def _enter_world(page: Page) -> None:
    if await page.locator(VILLAGE_MENU_SELECTOR).count():
        return

    server = settings.tw_server
    logger.info("Entering world {}", server)
    await page.goto(PLAY_URL.format(server=server), wait_until="domcontentloaded")
    try:
        await page.wait_for_selector(VILLAGE_MENU_SELECTOR, timeout=WORLD_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise UpstreamError(
            f"Não entrou no mundo {server} (url atual: {page.url}). "
            "Confira TW_SERVER e se a conta tem aldeia nesse mundo."
        ) from exc
