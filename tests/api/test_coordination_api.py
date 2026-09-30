from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.repositories.coordination import CoordinationRepository


async def test_coordination_is_empty_before_any_round(client: AsyncClient) -> None:
    response = await client.get("/api/v1/agents/coordination")

    assert response.status_code == 200
    assert response.json() == []


async def test_proposers_describe_every_specialist(client: AsyncClient) -> None:
    response = await client.get("/api/v1/agents/proposers")

    titles = {p["title"] for p in response.json()}
    assert {"Economia", "Infraestrutura", "Recrutamento", "Defesa", "Ataque", "Expansão", "Inteligência", "Mordomo"} <= titles


ROUND = {
    "executed": [
        {"title": "Quartel 2", "source": "infrastructure", "ok": True, "result": "na fila"},
        {"title": "Coleta", "source": "attack", "ok": False, "result": "RECUSADO: aprendido"},
        {"title": "Saque", "source": "attack", "ok": False, "result": "erro no jogo"},
    ],
    "deferred": [
        {"title": "Muralha 3", "source": "defense", "why": "consumiria recursos reservados para base"},
        {"title": "Lanceiros", "source": "recruitment", "why": "faltam 120 wood, disponível em ~1.0h"},
        {"title": "Fazenda 4", "source": "economy", "why": "fila de construção cheia"},
        {"title": "Mercado", "source": "economy", "why": "algo que o jogo recusou antes"},
    ],
}


async def save(session: AsyncSession, run_id: str, village_id: int) -> None:
    await CoordinationRepository(session).save_round(run_id, village_id, "growth", "growth", "crescer", None, ROUND)


async def test_a_run_explains_each_decision_with_a_kind(client: AsyncClient, session: AsyncSession) -> None:
    await save(session, "r1", 7)

    response = await client.get("/api/v1/agents/coordination/runs/r1")

    assert response.status_code == 200
    data = response.json()[0]["data"]
    assert [e["outcome"] for e in data["executed"]] == ["ok", "refused", "failed"]
    assert [e["why_kind"] for e in data["deferred"]] == ["reserved", "resources", "queue", "learned"]


async def test_an_unknown_run_is_not_found(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/agents/coordination/runs/nada")).status_code == 404


async def test_history_sums_each_run_across_villages(client: AsyncClient, session: AsyncSession) -> None:
    await save(session, "r1", 7)
    await save(session, "r1", 8)
    await save(session, "r2", 7)

    response = await client.get("/api/v1/agents/coordination/history", params={"limit": 5})

    runs = response.json()
    assert [r["run_id"] for r in runs] == ["r1", "r2"]
    assert runs[0]["villages"] == 2
    assert (runs[0]["executed"], runs[0]["refused"], runs[0]["failed"]) == (2, 2, 2)
    assert runs[0]["deferred"] == {"reserved": 2, "resources": 2, "queue": 2, "learned": 2}


async def test_history_keeps_only_the_latest_runs(client: AsyncClient, session: AsyncSession) -> None:
    for i in range(4):
        await save(session, f"r{i}", 7)

    runs = (await client.get("/api/v1/agents/coordination/history", params={"limit": 2, "village_id": 7})).json()

    assert [r["run_id"] for r in runs] == ["r2", "r3"]
