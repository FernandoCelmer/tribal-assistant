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
    log_store_level: str = Field(default="INFO")
    log_retention_days: int = Field(default=14)
    trace_retention_days: int = Field(default=30)

    database_url: str = Field(default="sqlite+aiosqlite:///./storage/tw.db")

    tw_world_url: str | None = None
    tw_username: str | None = None
    tw_password: str | None = None
    tw_server: str = "brxx"
    app_secret: str | None = None
    storage_dir: str = "./storage"

    play: bool = True
    headless: bool = False
    browser_state_path: str = "./storage/playwright-state.json"
    min_delay_ms: int = 1200
    max_delay_ms: int = 3800
    sync_interval_seconds: int = 120
    sync_report_details: bool = True
    world_sync_interval_minutes: int = 60
    quiet_hours: str | None = None
    html_capture_dir: str = "./storage/html"


    ai_provider: str = "none"
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    ai_max_steps: int = 10
    ai_max_tokens: int = 2048



settings = Settings()  # type: ignore[call-arg]
