"""Login + world select."""

from loguru import logger
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from tribal_assistant.core.accounts.context import current_account
from tribal_assistant.core.errors import UpstreamError
from tribal_assistant.core.game.human import human_delay

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
        logger.info("Sessão já ativa, formulário de login ignorado")

    await human_delay()
    await _enter_world(page)


async def _submit_credentials(page: Page) -> None:
    logger.info("Preenchendo credenciais")
    await page.fill("#user", current_account().username)
    await human_delay(400, 900)
    await page.fill("#password", current_account().password)
    await human_delay(400, 900)
    await page.click("a.btn-login")

    logger.info("Aguardando captcha/login (até {}s)", LOGIN_TIMEOUT_MS // 1000)
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

    server = current_account().server
    logger.info("Entrando no mundo {}", server)
    await page.goto(PLAY_URL.format(server=server), wait_until="domcontentloaded")
    try:
        await page.wait_for_selector(VILLAGE_MENU_SELECTOR, timeout=WORLD_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise UpstreamError(
            f"Não entrou no mundo {server} (url atual: {page.url}). "
            "Confira TW_SERVER e se a conta tem aldeia nesse mundo."
        ) from exc
