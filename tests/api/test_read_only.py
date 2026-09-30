import pytest
from httpx import AsyncClient

from tribal_assistant.api.readonly import READ_ONLY_MESSAGE
from tribal_assistant.core.config import settings


@pytest.fixture
def panel_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "play", False)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/assistant/sync"),
        ("POST", "/api/v1/knobs/tune"),
        ("PUT", "/api/v1/knobs/qualquer"),
        ("PATCH", "/api/v1/accounts/1"),
        ("PATCH", "/api/v1/agents/settings"),
        ("POST", "/api/v1/agents/run"),
        ("PUT", "/api/v1/agents/villages/1/role"),
        ("POST", "/api/v1/world/sync"),
        ("POST", "/api/v1/docs/sync"),
        ("POST", "/api/v1/accounts"),
    ],
)
async def test_a_panel_only_server_refuses_every_write(panel_only: None, client: AsyncClient, method: str, path: str) -> None:
    r = await client.request(method, path, json={"value": 0.5})

    assert r.status_code == 409
    assert r.json()["detail"] == {"code": "read_only", "message": READ_ONLY_MESSAGE}


async def test_a_panel_only_server_still_answers_reads(panel_only: None, client: AsyncClient) -> None:
    r = await client.get("/api/v1/knobs")

    assert r.status_code == 200


async def test_a_playing_server_accepts_writes(client: AsyncClient) -> None:
    r = await client.post("/api/v1/knobs/tune")

    assert r.status_code == 200
