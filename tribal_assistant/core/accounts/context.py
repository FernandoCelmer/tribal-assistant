"""The account the current task works for, carried by a context variable across async calls."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from tribal_assistant.core.config import settings


@dataclass(frozen=True)
class AccountContext:
    id: int
    name: str
    server: str
    world_url: str
    username: str
    password: str
    headless: bool = False

    @property
    def base_url(self) -> str:
        return self.world_url.rstrip("/")

    @property
    def state_path(self) -> Path:
        return Path(settings.storage_dir) / "sessions" / f"account-{self.id}.json"

    @property
    def capture_dir(self) -> Path:
        return Path(settings.html_capture_dir) / f"account-{self.id}"


_current: ContextVar[AccountContext | None] = ContextVar("tribal_account", default=None)


class NoAccountError(RuntimeError):
    pass


def current_account() -> AccountContext:
    account = _current.get()
    if account is None:
        raise NoAccountError("nenhuma conta selecionada; cadastre uma conta em /contas")

    return account


def current_account_id() -> int | None:
    account = _current.get()
    return account.id if account else None


def current_world() -> str | None:
    account = _current.get()
    return account.server if account else None


@contextmanager
def use_account(account: AccountContext) -> Iterator[AccountContext]:
    token = _current.set(account)
    try:
        yield account
    finally:
        _current.reset(token)
