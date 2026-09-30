"""Reaching game screens and reading pages the way a player would."""

from typing import Any

from loguru import logger
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from tribal_assistant.core.accounts.context import current_account
from tribal_assistant.core.game.human import human_click, reading_pause
from tribal_assistant.core.game.login import VILLAGE_MENU_SELECTOR, login, visit
from tribal_assistant.core.game.session import game_session

EVALUATE_ATTEMPTS = 3

BUILD_QUEUE_JS = """() => [...document.querySelectorAll('#buildqueue tr[class*="buildorder_"]')].map(tr => {
  const cls = [...tr.classList].find(c => c.startsWith('buildorder_')) || '';
  const timer = tr.querySelector('[data-endtime]');
  const cell = tr.querySelector('td');
  return {building: cls.slice('buildorder_'.length), text: cell ? cell.innerText : '',
    end: timer ? timer.dataset.endtime : null};
})"""

FIND_LINK_JS = """(want) => {
  const current = String((window.game_data && game_data.village && game_data.village.id) || '');
  document.querySelectorAll('a[data-tw-nav]').forEach(a => a.removeAttribute('data-tw-nav'));
  const link = [...document.querySelectorAll('a[href]')].find(a => {
    if (!a.offsetParent) return false;
    let url;
    try { url = new URL(a.getAttribute('href'), location.href); } catch { return false; }
    if (url.origin !== location.origin || !url.pathname.endsWith('/game.php')) return false;
    const q = url.searchParams;
    if (q.get('h') || q.get('action') || q.get('ajaxaction') || q.get('ajax')) return false;
    if ((q.get('village') || current) !== want.village) return false;
    for (const key of ['screen', 'mode', 'view']) {
      if ((q.get(key) || '') !== (want[key] || '')) return false;
    }
    return true;
  });
  if (!link) return false;
  link.setAttribute('data-tw-nav', '1');
  return true;
}"""


def screen_url(screen: str, village_id: str | None = None, **params: str) -> str:
    query = {"screen": screen, **params}
    if village_id:
        query = {"village": village_id, **query}
    return f"{current_account().base_url}/game.php?" + "&".join(
        f"{k}={v}" for k, v in query.items()
    )


async def open_screen(page: Page, screen: str, village_id: str | None = None, **params: str) -> None:
    """Reach a screen the way a player would: click its link when one is on the page."""
    found = False
    if village_id and page.url.startswith(current_account().base_url):
        want = {"screen": screen, "village": village_id, **params}
        try:
            found = bool(await page.evaluate(FIND_LINK_JS, want))
        except PlaywrightError:
            found = False

    if found:
        try:
            async with page.expect_navigation(wait_until="load", timeout=20_000):
                await human_click(page, page.locator('a[data-tw-nav="1"]').first)
        except PlaywrightError:
            logger.debug("Clique no link para {} não navegou, carregando URL", screen)
            found = False

    wanted = [f"screen={screen}", *(f"{k}={v}" for k, v in params.items())]
    if found and not all(part in page.url for part in wanted):
        logger.debug("Clique no link caiu em {} em vez de {}, carregando URL", page.url, screen)
        found = False

    if not found:
        await page.goto(screen_url(screen, village_id, **params), wait_until="load")
    await reading_pause(page)


async def evaluate_page(page: Page, script: str) -> Any:
    """Evaluate, retrying when the game redirects or reloads mid-read."""
    for attempt in range(1, EVALUATE_ATTEMPTS + 1):
        try:
            return await page.evaluate(script)
        except PlaywrightError as exc:
            if "Execution context was destroyed" not in str(exc) or attempt == EVALUATE_ATTEMPTS:
                raise
            logger.debug("Página navegou durante a leitura, tentando de novo ({}/{})", attempt, EVALUATE_ATTEMPTS)
            await page.wait_for_load_state("load")


async def ensure_in_game(page: Page) -> None:
    if page.url.startswith(current_account().base_url) and await page.locator(
        VILLAGE_MENU_SELECTOR
    ).count():
        return
    await visit(page, screen_url("overview"))
    await reading_pause(page)
    if not await page.locator(VILLAGE_MENU_SELECTOR).count():
        logger.info("Fora do jogo, fazendo login")
        await login(page)
        await game_session.save_state()
