from httpx import AsyncClient

from tribal_assistant.core.agents.knobs import Knobs


def share_knob() -> str:
    return next(name for name, spec in Knobs.SPECS.items() if spec.share)


def plain_knob() -> str:
    return next(name for name, spec in Knobs.SPECS.items() if not spec.share and not spec.integer)


async def test_lists_every_knob_at_its_default(client: AsyncClient) -> None:
    r = await client.get("/api/v1/knobs")

    assert r.status_code == 200
    items = {i["name"]: i for i in r.json()}
    assert set(items) == set(Knobs.SPECS)
    for name, spec in Knobs.SPECS.items():
        assert items[name]["value"] == spec.default
        assert items[name]["history"] == []
        assert items[name]["updated_at"] is None


async def test_manual_set_stores_value_reason_and_history(client: AsyncClient) -> None:
    name = plain_knob()

    r = await client.put(f"/api/v1/knobs/{name}", json={"value": 2.5})

    assert r.status_code == 200
    body = r.json()
    assert body["value"] == 2.5
    assert body["reason"] == "ajuste manual"
    assert body["history"][-1]["to"] == 2.5
    assert body["history"][-1]["from"] == 2.5
    listed = {i["name"]: i for i in (await client.get("/api/v1/knobs")).json()}
    assert listed[name]["value"] == 2.5


async def test_share_above_one_is_refused(client: AsyncClient) -> None:
    r = await client.put(f"/api/v1/knobs/{share_knob()}", json={"value": 1.5})

    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid"


async def test_non_positive_value_is_refused(client: AsyncClient) -> None:
    assert (await client.put(f"/api/v1/knobs/{plain_knob()}", json={"value": 0})).status_code == 422


async def test_unknown_knob_is_not_found(client: AsyncClient) -> None:
    r = await client.put("/api/v1/knobs/nao_existe", json={"value": 0.5})

    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "not_found"


async def test_tune_without_rounds_changes_nothing(client: AsyncClient) -> None:
    r = await client.post("/api/v1/knobs/tune")

    assert r.status_code == 200
    assert r.json() == {"changes": []}
    assert all(i["value"] == i["default"] for i in (await client.get("/api/v1/knobs")).json())
