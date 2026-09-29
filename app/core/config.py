"""Typed runtime configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    database_url: str = Field(default="sqlite+aiosqlite:///./storage/tw.db")

    tw_world_url: str
    tw_username: str
    tw_password: str
    tw_server: str = "brxx"

    headless: bool = False
    browser_state_path: str = "./storage/playwright-state.json"
    min_delay_ms: int = 1200
    max_delay_ms: int = 3800
    sync_interval_seconds: int = 120
    sync_report_details: bool = True
    world_sync_interval_minutes: int = 60
    quiet_hours: str | None = None

    farm_enabled: bool = True
    farm_min_loot: int = 10
    farm_max_wall_level: int = 1

    telegram_token: str | None = None
    telegram_chat_id: str | None = None


settings = Settings()  # type: ignore[call-arg]
