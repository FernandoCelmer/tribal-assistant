"""Refuses every write when the server only shows the panel and does not play."""

from fastapi import Request

from tribal_assistant.core.config import settings
from tribal_assistant.core.errors import ConflictError

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
READ_ONLY_MESSAGE = "este painel é só leitura: o servidor não joga (PLAY=false)"


class ReadOnlyError(ConflictError):
    code = "read_only"


def refuse_writes_when_not_playing(request: Request) -> None:
    if not settings.play and request.method in WRITE_METHODS:
        raise ReadOnlyError(READ_ONLY_MESSAGE)
