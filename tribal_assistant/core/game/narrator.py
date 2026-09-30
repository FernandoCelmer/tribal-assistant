"""Publishes the small steps behind each decision: the tool called with its arguments, the screen opened, the button clicked."""

import json
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator

from tribal_assistant.core.events import event_bus

KIND = "micro"
LABEL_TIMEOUT_MS = 400
MAX_LABEL = 60
MAX_ARGS = 240

SCREENS = {
    "overview": "visão geral",
    "overview_villages": "lista de aldeias",
    "main": "edifício principal",
    "train": "recrutamento",
    "barracks": "quartel",
    "stable": "estábulo",
    "garage": "oficina",
    "smith": "ferreiro",
    "snob": "academia",
    "place": "praça de reunião",
    "am_farm": "assistente de saque",
    "market": "mercado",
    "statue": "estátua do paladino",
    "inventory": "inventário",
    "relic_system": "tesouraria",
    "report": "relatórios",
    "mail": "mensagens",
    "forum": "fórum",
    "ally": "tribo",
    "info_ally": "perfil da tribo",
    "info_player": "perfil do jogador",
    "info_command": "comando",
    "info_village": "aldeia",
    "flags": "bandeiras",
    "mentor": "mentor",
    "buddies": "amigos",
    "settings": "configurações",
    "map": "mapa",
    "wood": "bosque",
    "stone": "poço de argila",
    "iron": "mina de ferro",
    "farm": "fazenda",
    "storage": "armazém",
    "wall": "muralha",
    "hide": "esconderijo",
}

LABEL_JS = """(n) => (n.innerText || n.value || n.getAttribute('data-title') || n.title || n.alt
  || n.getAttribute('aria-label') || n.getAttribute('name') || n.id || '').replace(/\\s+/g, ' ').trim()"""


class Narrator:
    @staticmethod
    def _publish(step: str, **data: Any) -> None:
        event_bus.publish(KIND, {"step": step, **data})

    @staticmethod
    def arguments(arguments: dict[str, Any]) -> str:
        shown = {k: v for k, v in arguments.items() if k != "reason" and v not in (None, "", [], {})}
        text = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False) if isinstance(v, dict | list) else v}" for k, v in shown.items())
        return text if len(text) <= MAX_ARGS else text[: MAX_ARGS - 1] + "…"

    @classmethod
    def tool(cls, agent: str, tool: str, arguments: dict[str, Any], village_id: int) -> None:
        cls._publish("tool", agent=agent, tool=tool, args=cls.arguments(arguments), village_id=village_id)

    @classmethod
    def result(cls, agent: str, tool: str, ok: bool, text: str, village_id: int) -> None:
        cls._publish("result", agent=agent, tool=tool, ok=ok, text=text, village_id=village_id)

    @classmethod
    def screen(cls, screen: str, params: dict[str, str]) -> None:
        name = SCREENS.get(params.get("building", "")) or SCREENS.get(screen, screen.replace("_", " "))
        mode = params.get("mode")
        cls._publish("screen", text=f"{name} ({mode.replace('_', ' ')})" if mode else name)

    @classmethod
    async def click(cls, target: Locator) -> None:
        try:
            label = str(await target.evaluate(LABEL_JS, timeout=LABEL_TIMEOUT_MS))
        except PlaywrightError:
            label = ""
        label = label[:MAX_LABEL] if label else "elemento"
        cls._publish("click", text=label)
