from httpx import AsyncClient


async def test_overview_empty(client: AsyncClient) -> None:
    r = await client.get("/api/v1/game/overview")
    assert r.status_code == 200
    assert r.json() == {"player": None, "villages": [], "commands": [], "reports": []}


async def test_world_status_empty(client: AsyncClient) -> None:
    r = await client.get("/api/v1/world/status")
    assert r.status_code == 200
    assert r.json()["villages"] == 0
