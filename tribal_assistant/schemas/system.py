"""Read-only runtime facts for the settings page (never secrets)."""

from pydantic import BaseModel


class AIInfo(BaseModel):
    provider: str
    model: str | None
    base_url: str | None
    key_configured: bool
    active: bool
    error: str | None


class SystemInfo(BaseModel):
    version: str
    world_url: str
    server: str
    sync_interval_seconds: int
    world_sync_interval_minutes: int
    quiet_hours: str | None
    headless: bool
    database: str
    log_retention_days: int
    trace_retention_days: int
    ai: AIInfo
