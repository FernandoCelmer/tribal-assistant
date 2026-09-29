"""Reads the whole account state from the browser and persists it."""

import random
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from tribal_assistant.client.human import human_click, reading_pause
from tribal_assistant.client.login import VILLAGE_MENU_SELECTOR, login
from tribal_assistant.client.scraper.game import (
    GameSnapshot,
    GameVillage,
    parse_player,
    parse_reports,
    parse_village,
)
from tribal_assistant.client.screens import ScreenCatalog
from tribal_assistant.client.session import game_session
from tribal_assistant.client.state import session_state
from tribal_assistant.core.config import settings
from tribal_assistant.core.errors import UpstreamError
from tribal_assistant.db.session import SessionFactory
from tribal_assistant.repositories.agent_settings import AgentSettingsRepository
from tribal_assistant.repositories.game import GameRepository

GAME_DATA_JS = "() => window.game_data || null"

UPGRADES_JS = """() => {
  const src = (window.BuildingMain && BuildingMain.buildings) || {};
  const out = {};
  for (const [id, b] of Object.entries(src)) {
    out[id] = {level_next: b.level_next, max_level: b.max_level, wood: b.wood, stone: b.stone,
      iron: b.iron, pop: b.pop, build_time: b.build_time, can_build: b.can_build, error: b.error};
  }
  return out;
}"""

BUILD_QUEUE_JS = """() => [...document.querySelectorAll('#buildqueue tr[class*="buildorder_"]')].map(tr => {
  const cls = [...tr.classList].find(c => c.startsWith('buildorder_')) || '';
  const timer = tr.querySelector('[data-endtime]');
  const cell = tr.querySelector('td');
  return {building: cls.slice('buildorder_'.length), text: cell ? cell.innerText : '',
    end: timer ? timer.dataset.endtime : null};
})"""

TRAIN_JS = r"""() => {
  const units = ((window.game_data && game_data.units) || []).filter(u => u !== 'militia');
  const text = (u, key) => { const e = document.getElementById(`${u}_0_${key}`); return e ? e.innerText.trim() : null; };
  const locked = [...document.querySelectorAll('#content_value table.vis tr')]
    .filter(tr => !tr.querySelector('input.recruit_unit'));
  return units.map(u => {
    const input = document.getElementById(`${u}_0`);
    const row = input ? input.closest('tr')
      : locked.find(tr => tr.querySelector(`[data-unit="${u}"], img[src*="unit_${u}."], img[src*="unit_${u}_"]`));
    let home = null, total = null, requirements = null;
    if (row) {
      const counts = row.innerText.match(/(\d+)\s*\/\s*(\d+)/);
      if (counts) { home = counts[1]; total = counts[2]; }
      if (!input) requirements = [...row.cells].slice(1).map(c => c.innerText.trim()).join(' ').replace(/\s+/g, ' ');
    }
    const max = document.getElementById(`${u}_0_a`);
    return {name: u, available: !!input, home, total, requirements,
      max: max ? (max.innerText.match(/\d+/) || [null])[0] : null,
      wood: text(u, 'cost_wood'), stone: text(u, 'cost_stone'), iron: text(u, 'cost_iron'),
      pop: text(u, 'cost_pop'), time: text(u, 'cost_time')};
  });
}"""

RECRUIT_QUEUE_JS = r"""() => {
  const units = (window.game_data && game_data.units) || [];
  return [...document.querySelectorAll('[id^="trainqueue_"] tr, .trainqueue_wrap tr')]
    .filter(tr => tr.querySelector('[data-endtime]'))
    .map(tr => {
      const sprite = tr.querySelector('[class*="unit_sprite"]');
      const classes = sprite ? sprite.className.split(/\s+/) : [];
      const unit = units.find(u => classes.includes(u)) || units.find(u => tr.innerHTML.includes(`unit_${u}`)) || '';
      return {unit, text: (tr.cells[0] || tr).innerText, end: tr.querySelector('[data-endtime]').dataset.endtime};
    });
}"""

HOME_UNITS_JS = """() => [...document.querySelectorAll('input[id^="unit_input_"]')].map(i => ({
  name: i.name || i.id.slice('unit_input_'.length), count: i.dataset.allCount}))"""

OVERVIEW_JS = """() => {
  const read = (sel, direction) => [...document.querySelectorAll(sel + ' tr')]
    .filter(tr => tr.querySelector('[data-endtime]'))
    .map(tr => {
      const img = tr.querySelector('img[src*="command/"]');
      const idEl = tr.querySelector('.quickedit[data-id]');
      return {direction, id: idEl ? idEl.dataset.id : null, icon: img ? img.getAttribute('src') : '',
        text: (tr.cells[0] || tr).innerText, end: tr.querySelector('[data-endtime]').dataset.endtime};
    });
  const banner = document.querySelector('#show_newbie') || document.querySelector('#content_value');
  return {commands: [...read('#show_incoming_units', 'in'), ...read('#show_outgoing_units', 'out')],
    text: banner ? banner.innerText : ''};
}"""

SCAVENGE_JS = """() => {
  const s = window.ScavengeScreen;
  if (!s || !s.village || !s.village.options) return [];
  const clean = v => v == null ? null : JSON.parse(JSON.stringify(v, (k, x) => k.startsWith('_') ? undefined : x));
  return Object.values(s.village.options).map(o => ({id: o.base.id, name: o.base.name,
    loot_factor: o.base.loot_factor, locked: o.is_locked, unlock_time: o.unlock_time,
    squad: clean(o.scavenging_squad)}));
}"""

VILLAGE_IDS_JS = """() => [...new Set([...document.querySelectorAll('#production_table .quickedit-vn')]
  .map(e => e.dataset.id).filter(Boolean))]"""

REPORTS_JS = r"""() => [...document.querySelectorAll('#report_list tr')]
  .filter(tr => tr.querySelector('.quickedit[data-id]'))
  .map(tr => {
    const q = tr.querySelector('.quickedit[data-id]');
    return {id: q.dataset.id, title: q.innerText, received: tr.cells[tr.cells.length - 1].innerText,
      icons: [...tr.querySelectorAll('img')].map(i => i.getAttribute('src')).join(' '),
      is_new: /\(nov[oa]\)/i.test(tr.innerText)};
  })"""

REPORT_DETAIL_JS = r"""() => {
  const text = s => { const e = document.querySelector(s); return e ? e.innerText : ''; };
  const results = document.querySelector('#attack_results');
  let loot = [], haul = '';
  if (results) {
    const row = [...results.querySelectorAll('tr')].find(r => /saque/i.test(r.innerText));
    if (row) {
      loot = [...row.querySelectorAll('.nowrap')].map(e => e.innerText);
      haul = (row.innerText.match(/\d+\s*\/\s*\d+/) || [''])[0];
    }
  }
  return {attacker: text('#attack_info_att'), defender: text('#attack_info_def'), loot, haul};
}"""

EVALUATE_ATTEMPTS = 3
REPORT_DETAILS_PER_SYNC = 5


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


def _url(screen: str, village_id: str | None = None, **params: str) -> str:
    query = {"screen": screen, **params}
    if village_id:
        query = {"village": village_id, **query}
    return f"{settings.tw_world_url.rstrip('/')}/game.php?" + "&".join(
        f"{k}={v}" for k, v in query.items()
    )


async def _open(page: Page, screen: str, village_id: str | None = None, **params: str) -> None:
    """Reach a screen the way a player would: click its link when one is on the page."""
    found = False
    if village_id and page.url.startswith(settings.tw_world_url.rstrip("/")):
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
            logger.debug("Link click to {} did not navigate, loading URL", screen)
            found = False

    if found and f"screen={screen}" not in page.url:
        logger.debug("Link click landed on {} instead of {}, loading URL", page.url, screen)
        found = False

    if not found:
        await page.goto(_url(screen, village_id, **params), wait_until="load")
    await reading_pause(page)


async def _evaluate(page: Page, script: str) -> Any:
    """Evaluate, retrying when the game redirects or reloads mid-read."""
    for attempt in range(1, EVALUATE_ATTEMPTS + 1):
        try:
            return await page.evaluate(script)
        except PlaywrightError as exc:
            if "Execution context was destroyed" not in str(exc) or attempt == EVALUATE_ATTEMPTS:
                raise
            logger.debug("Page navigated during read, retrying ({}/{})", attempt, EVALUATE_ATTEMPTS)
            await page.wait_for_load_state("load")


async def _game_data(page: Page) -> dict[str, Any]:
    data = await _evaluate(page, GAME_DATA_JS)
    if not data:
        raise UpstreamError(f"game_data ausente em {page.url}")
    return data


async def _ensure_in_game(page: Page) -> None:
    if page.url.startswith(settings.tw_world_url.rstrip("/")) and await page.locator(
        VILLAGE_MENU_SELECTOR
    ).count():
        return
    await page.goto(_url("overview"), wait_until="load")
    await reading_pause(page)
    if not await page.locator(VILLAGE_MENU_SELECTOR).count():
        logger.info("Not in game, logging in")
        await login(page)
        await game_session.save_state()


async def _own_village_ids(page: Page, game_data: dict[str, Any], count: int) -> list[str]:
    current = str(game_data["village"]["id"])
    if count <= 1:
        return [current]
    await _open(page, "overview_villages", current, mode="prod")
    ids = await _evaluate(page, VILLAGE_IDS_JS)
    return ids or [current]


async def _read_village(page: Page, village_id: str, finish_free: bool = False) -> tuple[GameVillage, str]:
    async def overview() -> dict[str, Any]:
        await _open(page, "overview", village_id)
        return {"overview": await _evaluate(page, OVERVIEW_JS)}

    async def main() -> dict[str, Any]:
        await _open(page, "main", village_id)

        if finish_free:
            from tribal_assistant.client.actions import GameActions

            await GameActions().click_free_finish(page)

        return {
            "game_data": await _game_data(page),
            "upgrades": await _evaluate(page, UPGRADES_JS),
            "build_queue": await _evaluate(page, BUILD_QUEUE_JS),
        }

    async def train() -> dict[str, Any]:
        await _open(page, "train", village_id)
        return {
            "units": await _evaluate(page, TRAIN_JS),
            "recruit": await _evaluate(page, RECRUIT_QUEUE_JS),
        }

    async def place() -> dict[str, Any]:
        await _open(page, "place", village_id)
        return {"home": await _evaluate(page, HOME_UNITS_JS)}

    async def scavenge() -> dict[str, Any]:
        await _open(page, "place", village_id, mode="scavenge")
        return {"scavenge": await _evaluate(page, SCAVENGE_JS)}

    readers = [overview, main, train, place, scavenge]
    random.shuffle(readers)
    data: dict[str, Any] = {}
    for reader in readers:
        data.update(await reader())

    village = parse_village(
        data["game_data"],
        data["upgrades"],
        data["build_queue"],
        data["units"],
        home_rows=data["home"],
        recruit_rows=data["recruit"],
        command_rows=data["overview"]["commands"],
        scavenge_rows=data["scavenge"],
    )

    catalog = ScreenCatalog()
    missing = catalog.missing({b.name: b.level for b in village.buildings})
    for name in missing[:3]:
        try:
            await catalog.capture(page, village_id, name)
        except PlaywrightError as exc:
            logger.warning("Could not capture {} screen: {}", name, exc)

    return village, data["overview"]["text"]


async def _read_reports(page: Page, village_id: str, known: set[str]) -> list[dict[str, Any]]:
    await _open(page, "report", village_id, mode="all")
    rows: list[dict[str, Any]] = await _evaluate(page, REPORTS_JS)
    if not settings.sync_report_details:
        return rows

    pending = [
        r for r in rows if r["id"] not in known and "ataca" in str(r.get("title", "")).lower()
    ][:REPORT_DETAILS_PER_SYNC]
    for row in pending:
        await _open(page, "report", village_id, mode="all", view=row["id"])
        row["detail"] = await _evaluate(page, REPORT_DETAIL_JS)
    return rows


async def _read_game(known_reports: set[str], finish_free: bool = False) -> GameSnapshot:
    page = await game_session.page()
    await _ensure_in_game(page)

    game_data = await _game_data(page)
    first = parse_player(game_data)
    village_ids = await _own_village_ids(page, game_data, first.villages)

    villages = []
    overview_text = ""
    for village_id in village_ids:
        village, text = await _read_village(page, village_id, finish_free)
        villages.append(village)
        overview_text = overview_text or text

    report_rows: list[dict[str, Any]] = []
    if first.new_reports or not known_reports:
        report_rows = await _read_reports(page, village_ids[0], known_reports)
    player = parse_player(await _game_data(page), overview_text)

    await game_session.save_state()
    return GameSnapshot(
        player=player,
        villages=tuple(villages),
        reports=parse_reports(
            report_rows, {r["id"]: r["detail"] for r in report_rows if r.get("detail")}
        ),
    )


async def sync_game() -> GameSnapshot:
    async with game_session.lock:
        try:
            async with SessionFactory() as session:
                known = await GameRepository(session).report_ids()
                config = await AgentSettingsRepository(session).get()
            snapshot = await _read_game(known, config.auto_finish_free)
            async with SessionFactory() as session:
                await GameRepository(session).persist(snapshot)
        except Exception as exc:
            session_state.logged_in = False
            session_state.last_error = str(exc)
            raise
    session_state.logged_in = True
    session_state.last_error = None
    session_state.last_sync_at = datetime.now(UTC)
    logger.info(
        "Synced {} village(s), {} report(s)", len(snapshot.villages), len(snapshot.reports)
    )
    return snapshot
