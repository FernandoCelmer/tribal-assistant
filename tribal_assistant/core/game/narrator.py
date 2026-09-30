"""Publishes the small steps behind each decision: the tool called with its arguments, the screen opened, the button clicked."""

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Frame, Locator, Page, Request

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

FIELD_JS = """(n) => ({type: (n.type || '').toLowerCase(), name: (n.getAttribute('name') || n.id || n.placeholder
  || n.getAttribute('aria-label') || n.tagName || '').toString().trim()})"""
MAX_TYPED = 60
SECRET_FIELDS = ("pass", "senha", "token")

LABEL_JS = """(n) => (n.innerText || n.value || n.getAttribute('data-title') || n.title || n.alt
  || n.getAttribute('aria-label') || n.getAttribute('name') || n.id || '').replace(/\\s+/g, ' ').trim()"""


GAME_PATH = "/game.php"
PAUSE_SECONDS = 2.0


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

    @staticmethod
    def place(screen: str, params: dict[str, str]) -> str:
        name = SCREENS.get(params.get("building", "")) or SCREENS.get(screen, screen.replace("_", " "))
        mode = params.get("mode")
        return f"{name} ({mode.replace('_', ' ')})" if mode else name

    @staticmethod
    def query(url: str) -> dict[str, str] | None:
        parsed = urlparse(url)
        if parsed.path != GAME_PATH:
            return None
        return {k: v[0] for k, v in parse_qs(parsed.query).items()}

    @classmethod
    def watch(cls, page: Page) -> None:
        page.on("framenavigated", lambda frame: cls.navigated(page, frame))
        page.on("request", cls.request)

    @classmethod
    def navigated(cls, page: Page, frame: Frame) -> None:
        if frame != page.main_frame:
            return
        params = cls.query(frame.url)
        if params is None:
            cls._publish("screen", text=urlparse(frame.url).netloc or "página")
            return
        cls._publish("screen", text=cls.place(params.get("screen", "overview"), params))

    @classmethod
    def request(cls, request: Request) -> None:
        if request.method != "POST" and request.resource_type != "xhr":
            return
        params = cls.query(request.url)
        if params is None:
            return
        action = params.get("ajaxaction") or params.get("action")
        if not action:
            return
        where = cls.place(params.get("screen", ""), params) if params.get("screen") else ""
        cls._publish("request", text=action.replace("_", " "), where=where, method=request.method)

    @classmethod
    async def typing(cls, target: Locator, text: str) -> None:
        if not text:
            return
        try:
            field = dict(await target.evaluate(FIELD_JS, timeout=LABEL_TIMEOUT_MS))
        except Exception:
            field = {"type": "", "name": ""}
        name = str(field.get("name") or "campo")[:MAX_LABEL]
        secret = field.get("type") == "password" or any(word in name.lower() for word in SECRET_FIELDS)
        shown = "••••" if secret else (text if len(text) <= MAX_TYPED else text[: MAX_TYPED - 1] + "…")
        cls._publish("type", text=shown, field=name)

    @classmethod
    def motion(cls, text: str) -> None:
        cls._publish("motion", text=text)

    @classmethod
    def pause(cls, seconds: float) -> None:
        if seconds >= PAUSE_SECONDS:
            cls._publish("motion", text=f"pausa de {seconds:.0f}s, como um jogador")

    @classmethod
    async def click(cls, target: Locator) -> None:
        try:
            label = str(await target.evaluate(LABEL_JS, timeout=LABEL_TIMEOUT_MS))
        except Exception:
            label = ""
        label = label[:MAX_LABEL] if label else "elemento"
        cls._publish("click", text=label)
