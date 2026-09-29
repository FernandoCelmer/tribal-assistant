from httpx import AsyncClient


async def test_coordination_is_empty_before_any_round(client: AsyncClient) -> None:
    response = await client.get("/api/v1/agents/coordination")

    assert response.status_code == 200
    assert response.json() == []


async def test_proposers_describe_every_specialist(client: AsyncClient) -> None:
    response = await client.get("/api/v1/agents/proposers")

    titles = {p["title"] for p in response.json()}
    assert {"Economia", "Infraestrutura", "Recrutamento", "Defesa", "Ataque", "Expansão", "Inteligência", "Mordomo"} <= titles
