import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.repositories.agent_settings import AgentSettingsRepository
from tribal_assistant.schemas.agent_settings import AgentSettings, AgentSettingsUpdate


async def test_defaults_are_created_on_first_read(session: AsyncSession) -> None:
    settings = await AgentSettingsRepository(session).get()

    assert settings == AgentSettings()
    assert settings.enabled is False


async def test_update_changes_only_given_fields(session: AsyncSession) -> None:
    repo = AgentSettingsRepository(session)

    updated = await repo.update(AgentSettingsUpdate(enabled=True, attack_radius=8))

    assert updated.enabled is True
    assert updated.attack_radius == 8
    assert updated.interval_minutes == AgentSettings().interval_minutes
    assert await repo.get() == updated


async def test_mark_run_records_timestamp(session: AsyncSession) -> None:
    repo = AgentSettingsRepository(session)

    assert await repo.last_run_at() is None
    await repo.mark_run()
    assert await repo.last_run_at() is not None


def test_update_rejects_out_of_range_and_unknown_keys() -> None:
    with pytest.raises(ValidationError):
        AgentSettingsUpdate(attack_radius=500)

    with pytest.raises(ValidationError):
        AgentSettingsUpdate.model_validate({"enable": True})


async def test_settings_api_roundtrip(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/agents/settings")).json()["enabled"] is False

    response = await client.patch("/api/v1/agents/settings", json={"enabled": True, "interval_minutes": 15})
    assert response.status_code == 200
    assert response.json()["interval_minutes"] == 15

    assert (await client.patch("/api/v1/agents/settings", json={"attack_radius": 0})).status_code == 422


def test_legacy_plan_refresh_hours_becomes_minutes():
    from tribal_assistant.schemas.agent_settings import AgentSettings

    assert AgentSettings.model_validate({"plan_refresh_hours": 2}).plan_refresh_minutes == 120


def test_legacy_hours_win_over_merged_defaults():
    from tribal_assistant.schemas.agent_settings import AgentSettings

    merged = {**AgentSettings().model_dump(), "plan_refresh_hours": 1}
    assert AgentSettings.model_validate(merged).plan_refresh_minutes == 60
