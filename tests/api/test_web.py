import pytest
from httpx import AsyncClient


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/", "text/html"),
        ("/design", "text/html"),
        ("/static/tribal.css", "text/css"),
        ("/static/shell.js", "javascript"),
        ("/static/icons.svg", "image/svg+xml"),
    ],
)
async def test_web_assets_are_served(client: AsyncClient, path: str, content_type: str) -> None:
    response = await client.get(path)
    assert response.status_code == 200
    assert content_type in response.headers["content-type"]
