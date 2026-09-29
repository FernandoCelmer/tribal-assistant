"""Tool annotation presets and the guard that turns domain errors into MCP tool errors."""

import functools
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from tribal_assistant.ai.errors import LLMError
from tribal_assistant.core.errors import DomainError

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
WRITES_LOCAL = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
REACHES_OUT = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True)


class GuardedTool:
    """Registers a coroutine as an MCP tool; domain errors surface as the tool's error text."""

    def __init__(self, mcp: MCPServer, **options: Any) -> None:
        self.mcp = mcp
        self.options = options

    def __call__(self, fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(fn)
        async def guarded(*args: Any, **kwargs: Any) -> Any:
            try:
                return await fn(*args, **kwargs)
            except (DomainError, LLMError) as exc:
                raise ToolError(str(exc)) from exc

        return self.mcp.tool(**self.options)(guarded)
