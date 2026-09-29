"""Server-rendered dashboard pages: one template per page, shared layout and navigation."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from tribal_assistant.version import __version__


@dataclass(frozen=True)
class PageSpec:
    key: str
    path: str
    label: str
    template: str
    group: str = ""
    icon: str = ""
    in_nav: bool = True


class BannerArt:
    """Inline style for the home banner when a painted scene was dropped in static/art."""

    NAMES = ("banner.webp", "banner.jpg", "banner.png")

    def __init__(self, static_dir: Path) -> None:
        self.static_dir = static_dir

    def style(self) -> str:
        for name in self.NAMES:
            if (self.static_dir / "art" / name).is_file():
                return f' style="--banner-art: url(/static/art/{name})"'
        return ""


class WebPages:
    PAGES: tuple[PageSpec, ...] = (
        PageSpec("overview", "/", "Visão geral", "overview.html", "Jogo", "crown"),
        PageSpec("village", "/aldeia", "Aldeia", "village.html", "Jogo", "castle"),
        PageSpec("surroundings", "/arredores", "Arredores", "surroundings.html", "Jogo", "globe"),
        PageSpec("reports", "/relatorios", "Relatórios", "reports.html", "Jogo", "scroll"),
        PageSpec("farm", "/farm", "Farm", "farm.html", "Jogo", "swords"),
        PageSpec("strategy", "/estrategia", "Estratégia", "strategy.html", "Agentes", "compass"),
        PageSpec("agents", "/agentes", "Agentes", "agents.html", "Agentes", "shield"),
        PageSpec("charts", "/graficos", "Gráficos", "charts.html", "Agentes", "star"),
        PageSpec("flow", "/grafos", "Grafos", "flow.html", "Agentes", "compass"),
        PageSpec("logs", "/logs", "Logs", "logs.html", "Agentes", "book"),
        PageSpec("accounts", "/contas", "Contas", "accounts.html", "Sistema", "key"),
        PageSpec("settings", "/configuracoes", "Configurações", "settings.html", "Sistema", "gear"),
        PageSpec("design", "/componentes", "Componentes", "design.html", in_nav=False),
    )

    REDIRECTS: ClassVar[dict[str, str]] = {"/agents": "/agentes", "/design": "/componentes"}

    def __init__(self, web_dir: Path) -> None:
        self.web_dir = web_dir
        self.templates = Jinja2Templates(directory=web_dir / "templates")
        self.banner = BannerArt(web_dir / "static")

    @property
    def nav(self) -> list[PageSpec]:
        return [page for page in self.PAGES if page.in_nav]

    @property
    def groups(self) -> list[tuple[str, list[PageSpec]]]:
        grouped: dict[str, list[PageSpec]] = {}
        for page in self.nav:
            grouped.setdefault(page.group, []).append(page)
        return list(grouped.items())

    def register(self, app: FastAPI) -> None:
        for spec in self.PAGES:
            app.add_api_route(spec.path, self._handler(spec), methods=["GET"], include_in_schema=False, response_class=HTMLResponse)

        for source, target in self.REDIRECTS.items():
            app.add_api_route(source, self._redirect(target), methods=["GET"], include_in_schema=False)

    def _handler(self, spec: PageSpec) -> Callable[[Request], Awaitable[HTMLResponse]]:
        async def render(request: Request) -> HTMLResponse:
            accounts, current = await self._accounts(request)
            return self.templates.TemplateResponse(
                request,
                f"pages/{spec.template}",
                {
                    "page": spec.key,
                    "nav": self.nav,
                    "groups": self.groups,
                    "current_label": spec.label,
                    "banner_style": self.banner.style() if spec.key == "overview" else "",
                    "version": __version__,
                    "accounts": accounts,
                    "current_account": current,
                },
                headers={"Cache-Control": "no-cache"},
            )

        return render

    @staticmethod
    async def _accounts(request: Request) -> tuple[list, int | None]:
        from tribal_assistant.db.session import SessionFactory, requested_account
        from tribal_assistant.repositories.accounts import AccountRepository

        try:
            async with SessionFactory() as session:
                accounts = list(await AccountRepository(session).list())
        except Exception:
            return [], None

        wanted = requested_account(request)
        ids = [a.id for a in accounts]
        current = wanted if wanted in ids else next((a.id for a in accounts if a.enabled), ids[0] if ids else None)
        return accounts, current

    @staticmethod
    def _redirect(target: str) -> Callable[[], Awaitable[RedirectResponse]]:
        async def redirect() -> RedirectResponse:
            return RedirectResponse(target, status_code=308)

        return redirect
