import pytest
from httpx import AsyncClient

PAGES = ["/", "/aldeia", "/arredores", "/relatorios", "/farm", "/agentes", "/graficos", "/grafos", "/logs", "/configuracoes", "/componentes"]


@pytest.mark.parametrize("path", PAGES)
async def test_pages_render_with_navigation(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    for link in PAGES[:-1]:
        assert f'href="{link}"' in response.text
    assert 'aria-current="page"' in response.text or path == "/componentes"


@pytest.mark.parametrize(("old", "new"), [("/agents", "/agentes"), ("/design", "/componentes")])
async def test_old_addresses_redirect(client: AsyncClient, old: str, new: str) -> None:
    response = await client.get(old)

    assert response.status_code == 308
    assert response.headers["location"] == new


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/static/tribal.css", "text/css"),
        ("/static/shell.js", "javascript"),
        ("/static/icons.svg", "image/svg+xml"),
        ("/static/js/core.js", "javascript"),
        ("/static/js/charts.js", "javascript"),
        ("/static/js/flow.js", "javascript"),
    ],
)
async def test_static_assets_are_served(client: AsyncClient, path: str, content_type: str) -> None:
    response = await client.get(path)

    assert response.status_code == 200
    assert content_type in response.headers["content-type"]


async def test_dashboard_skips_missing_banner_art(client: AsyncClient) -> None:
    response = await client.get("/")
    assert "--banner-art" not in response.text


def test_banner_art_used_when_present(tmp_path) -> None:
    from tribal_assistant.api.pages import BannerArt

    (tmp_path / "art").mkdir()
    (tmp_path / "art" / "banner.jpg").write_bytes(b"jpg")

    assert BannerArt(tmp_path).style() == ' style="--banner-art: url(/static/art/banner.jpg)"'


async def test_system_info_never_exposes_secrets(client: AsyncClient) -> None:
    response = await client.get("/api/v1/system/info")

    assert response.status_code == 200
    body = response.text.lower()
    assert "password" not in body and "api_key" not in body
    assert "key_configured" in body
