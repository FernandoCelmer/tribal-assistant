"""Walks through game pages like a curious player: rankings, neighbours, tribes, map and reports, reading each one."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from tribal_assistant.core.accounts.context import current_account
from tribal_assistant.core.game.human import reading_pause
from tribal_assistant.core.game.result import ActionResult
from tribal_assistant.core.game.session import game_session

if TYPE_CHECKING:
    from tribal_assistant.core.game.actions import GameActions

ACTION = "browse_game"
SAFE_SCREENS = frozenset(
    {"ranking", "info_player", "info_ally", "info_village", "ally", "map", "report", "buddies", "mail", "overview", "main", "place", "market", "statue", "flags", "inventory"}
)
READ_JS = """() => {
  const root = document.querySelector('#content_value') || document.body;
  const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
  const pairs = {};
  for (const tr of root.querySelectorAll('tr')) {
    const cells = [...tr.children].filter(c => c.tagName === 'TD' || c.tagName === 'TH');
    if (cells.length !== 2) continue;
    const raw = clean(cells[0].innerText);
    const value = clean(cells[1].innerText);
    if (!raw.endsWith(':') || !value || raw.length > 41 || value.length > 80) continue;
    const label = raw.slice(0, -1).trim();
    if (!(label in pairs)) pairs[label] = value;
  }
  const text = clean(root.innerText);
  const heading = clean((root.querySelector('h2, h3') || {}).innerText || document.title);
  return {heading, pairs, coords: [...new Set(text.match(/\\d{1,3}\\|\\d{1,3}/g) || [])].slice(0, 300), text: text.slice(0, 1500)};
}"""
MAX_HEADING = 60


class Wanderer:
    def __init__(self, actions: GameActions) -> None:
        self.actions = actions

    async def _sample(self, page: Any, screen: str, params: dict[str, str]) -> None:
        """Keeps one copy of each kind of page, so its reader can be written against the real markup."""
        modes = sorted(v for k, v in params.items() if k != "id")
        name = "-".join(["tour", screen, *modes, *(["profile"] if "id" in params else [])])
        directory = current_account().capture_dir
        if not any(directory.glob(f"{name}-*.html")):
            self.actions._capture(await page.content(), name)

    async def tour(self, village_id: str, stops: list[dict[str, Any]]) -> ActionResult:
        seen: list[str] = []
        pages: list[dict[str, Any]] = []
        async with game_session.lock:
            for stop in stops:
                screen = str(stop.get("screen", ""))
                if screen not in SAFE_SCREENS:
                    continue
                params = {str(k): str(v) for k, v in dict(stop.get("params") or {}).items()}
                try:
                    page = await self.actions._in_game(village_id, screen, **params)
                    await reading_pause(page)
                    read = dict(await page.evaluate(READ_JS) or {})
                except Exception as exc:
                    logger.warning("Passeio: {} não abriu: {}", screen, exc)
                    continue
                await self._sample(page, screen, params)
                heading = str(read.get("heading") or "")[:MAX_HEADING]
                label = str(stop.get("label") or heading or screen)
                seen.append(label)
                pages.append({**read, "screen": screen, "params": params, "label": label})

        if not seen:
            return ActionResult(False, ACTION, "nenhuma página visitada")

        logger.info("Passeio pelo jogo: {}", "; ".join(seen))
        return ActionResult(True, ACTION, f"visitou {len(seen)} página(s): {'; '.join(seen)}", {"pages": seen, "read": pages})
