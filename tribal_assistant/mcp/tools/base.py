"""A set of related MCP tools registered together; every tool calls the API."""

from abc import ABC, abstractmethod

from mcp.server.mcpserver import MCPServer

from tribal_assistant.mcp.client import ApiClient


class ToolGroup(ABC):
    def __init__(self, api: ApiClient | None = None) -> None:
        self.api = api or ApiClient()

    @abstractmethod
    def register(self, mcp: MCPServer) -> None:
        """Declare this group's tools on the server."""
