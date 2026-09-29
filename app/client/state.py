"""In-process game session state, shared by the scheduler jobs and the API."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SessionState:
    logged_in: bool = False
    last_sync_at: datetime | None = None
    last_error: str | None = None


session_state = SessionState()
