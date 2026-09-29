"""In-process game session state, shared by the scheduler jobs and the API."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SessionState:
    logged_in: bool = False
    last_sync_at: datetime | None = None
    last_error: str | None = None


class SessionStates:
    """Per-account session state; attribute access goes to the current account's state."""

    def __init__(self) -> None:
        object.__setattr__(self, "states", {})

    def get(self) -> SessionState:
        from tribal_assistant.accounts.context import current_account_id

        key = current_account_id() or 0
        return self.states.setdefault(key, SessionState())

    def __getattr__(self, name: str):
        return getattr(self.get(), name)

    def __setattr__(self, name: str, value) -> None:
        setattr(self.get(), name, value)


session_state = SessionStates()
