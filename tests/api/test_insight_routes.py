from datetime import datetime

import pytest
from httpx import AsyncClient

from tribal_assistant.core.config import settings
from tribal_assistant.core.models.report import Report


async def test_reports_page_is_empty_without_sync(client: AsyncClient) -> None:
    r = await client.get("/api/v1/game/reports", params={"offset": 0, "limit": 10})

    assert r.status_code == 200
    assert r.json() == {"total": 0, "offset": 0, "limit": 10, "items": []}


async def test_reports_page_pages_newest_first(client: AsyncClient, session) -> None:
    for day in range(1, 4):
        session.add(Report(game_id=str(day), title=f"r{day}", category="attack", result="green", received_at=datetime(2026, 9, day), target_coords="500|500"))
    await session.commit()

    r = await client.get("/api/v1/game/reports", params={"limit": 2, "category": "attack"})
    page = r.json()

    assert page["total"] == 3
    assert [i["game_id"] for i in page["items"]] == ["3", "2"]
    assert (await client.get("/api/v1/game/reports", params={"offset": 2})).json()["items"][0]["game_id"] == "1"


async def test_forecast_and_scavenge_plan_are_empty_without_villages(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/game/forecast")).json() == []
    assert (await client.get("/api/v1/game/scavenge-plan")).json() == []
    assert (await client.get("/api/v1/game/forecast", params={"village_id": 9})).status_code == 404


@pytest.mark.parametrize("path", ["/api/v1/game/market", "/api/v1/game/knight", "/api/v1/game/inventory"])
async def test_live_routes_need_the_playing_server(client: AsyncClient, monkeypatch, path: str) -> None:
    monkeypatch.setattr(settings, "play", False)

    r = await client.get(path)

    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "conflict"


@pytest.mark.parametrize("path", ["/api/v1/game/market", "/api/v1/game/knight", "/api/v1/game/inventory"])
async def test_live_routes_need_a_synced_village(client: AsyncClient, monkeypatch, path: str) -> None:
    monkeypatch.setattr(settings, "play", True)

    assert (await client.get(path)).status_code == 404


async def test_world_config_has_defaults_without_world_data(client: AsyncClient) -> None:
    r = await client.get("/api/v1/world/config")

    assert r.status_code == 200
    assert r.json()["speed"] == 1.0
