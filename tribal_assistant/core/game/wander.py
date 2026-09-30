"""Walks through game pages like a curious player: rankings, neighbours, tribes, map and reports, reading each one."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from tribal_assistant.core.game.human import reading_pause
from tribal_assistant.core.game.result import ActionResult
from tribal_assistant.core.game.session import game_session

if TYPE_CHECKING:
    from tribal_assistant.core.game.actions import GameActions

ACTION = "browse_game"
SAFE_SCREENS = frozenset(
    {"ranking", "info_player", "info_ally", "info_village", "ally", "map", "report", "buddies", "mail", "overview", "main", "place", "market", "statue", "flags", "inventory"}
)
HEADING_JS = "() => (document.querySelector('#content_value h2, #content_value h3, h2')?.innerText || document.title || '').replace(/\\s+/g, ' ').trim()"
MAX_HEADING = 60


class Wanderer:
    def __init__(self, actions: GameActions) -> None:
        self.actions = actions

    async def tour(self, village_id: str, stops: list[dict[str, Any]]) -> ActionResult:
        seen: list[str] = []
        async with game_session.lock:
            for stop in stops:
                screen = str(stop.get("screen", ""))
                if screen not in SAFE_SCREENS:
                    continue
                params = {str(k): str(v) for k, v in dict(stop.get("params") or {}).items()}
                try:
                    page = await self.actions._in_game(village_id, screen, **params)
                    await reading_pause(page)
                    heading = str(await page.evaluate(HEADING_JS))[:MAX_HEADING]
                except Exception as exc:
                    logger.warning("Passeio: {} não abriu: {}", screen, exc)
                    continue
                seen.append(str(stop.get("label") or heading or screen))

        if not seen:
            return ActionResult(False, ACTION, "nenhuma página visitada")

        logger.info("Passeio pelo jogo: {}", "; ".join(seen))
        return ActionResult(True, ACTION, f"visitou {len(seen)} página(s): {'; '.join(seen)}", {"pages": seen})
