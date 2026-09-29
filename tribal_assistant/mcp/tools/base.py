"""A set of related MCP tools registered together."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TypeVar

from mcp.server.mcpserver import MCPServer

from tribal_assistant.core.db.session import SessionFactory, init_db

T = TypeVar("T")


class ToolGroup(ABC):
    @abstractmethod
    def register(self, mcp: MCPServer) -> None:
        """Declare this group's tools on the server."""

    @staticmethod
    async def with_session(fn: Callable[..., Awaitable[T]]) -> T:
        await init_db()
        async with SessionFactory() as session:
            return await fn(session)
