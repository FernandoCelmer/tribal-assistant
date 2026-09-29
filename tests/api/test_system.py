from httpx import AsyncClient


async def test_system_info_never_exposes_secrets(client: AsyncClient) -> None:
    response = await client.get("/api/v1/system/info")

    assert response.status_code == 200
    body = response.text.lower()
    assert "password" not in body and "api_key" not in body
    assert "key_configured" in body
