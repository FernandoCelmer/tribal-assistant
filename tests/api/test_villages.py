from httpx import AsyncClient


async def test_upsert_and_list(client: AsyncClient) -> None:
    payload = {
        "name": "Home",
        "coords": "500|500",
        "is_own": True,
        "wood": 100,
        "clay": 200,
        "iron": 300,
        "storage": 1000,
        "pop_current": 24,
        "pop_max": 240,
    }
    r = await client.post("/api/v1/villages", json=payload)
    assert r.status_code == 201
    village = r.json()
    assert village["coords"] == "500|500"

    r = await client.get("/api/v1/villages")
    assert r.status_code == 200
    assert any(v["coords"] == "500|500" for v in r.json())


async def test_get_missing_returns_404(client: AsyncClient) -> None:
    r = await client.get("/api/v1/villages/999")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "not_found"
