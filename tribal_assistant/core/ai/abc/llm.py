"""Abstract LLM and conversation: every provider implements these two classes."""

from abc import ABC, abstractmethod

from tribal_assistant.core.ai.types import Reply, ToolResult, ToolSpec


class Conversation(ABC):
    """One tool-calling exchange; keeps the provider's native history across turns."""

    @abstractmethod
    async def send(self, results: list[ToolResult] | None = None) -> Reply:
        """Send pending tool results (or the opening prompt) and return the model's reply."""


class LLM(ABC):
    """A configured model on one provider."""

    provider: str
    model: str

    @abstractmethod
    def conversation(self, system: str, prompt: str, tools: list[ToolSpec]) -> Conversation:
        """Start a conversation with a system prompt, the first user message and the tools on offer."""
