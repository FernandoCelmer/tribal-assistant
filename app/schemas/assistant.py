from datetime import datetime

from pydantic import BaseModel


class AssistantStatus(BaseModel):
    running: bool
    logged_in: bool
    world: str
    scheduler_jobs: list[str] = []
    last_sync_at: datetime | None = None
    last_error: str | None = None


class CommandResult(BaseModel):
    ok: bool
    message: str
