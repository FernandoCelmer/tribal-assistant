"""Claude through the official Anthropic SDK."""

from typing import Any

import anthropic

from tribal_assistant.core.ai.abc.llm import LLM, Conversation
from tribal_assistant.core.ai.errors import LLMError
from tribal_assistant.core.ai.types import Reply, ToolCall, ToolResult, ToolSpec

FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = ("claude-opus-5", "claude-fable-5")


def _uses_adaptive_thinking(model: str) -> bool:
    return "haiku" not in model and not model.startswith("claude-3")


def _uses_fallbacks(model: str) -> bool:
    return model.startswith(FALLBACK_MODELS)


class AnthropicConversation(Conversation):
    def __init__(self, llm: "AnthropicLLM", system: str, prompt: str, tools: list[ToolSpec]) -> None:
        self.llm = llm
        self.system = system
        self.tools = [
            {"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools
        ]
        self.messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

    async def send(self, results: list[ToolResult] | None = None) -> Reply:
        if results:
            self.messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": r.call_id,
                            "content": r.content,
                            "is_error": r.is_error,
                        }
                        for r in results
                    ],
                }
            )

        request: dict[str, Any] = {
            "model": self.llm.model,
            "max_tokens": self.llm.max_tokens,
            "system": self.system,
            "tools": self.tools,
            "messages": self.messages,
        }
        if _uses_adaptive_thinking(self.llm.model):
            request["thinking"] = {"type": "adaptive"}

        try:
            if _uses_fallbacks(self.llm.model):
                response = await self.llm.client.beta.messages.create(
                    **request, betas=[FALLBACK_BETA], fallbacks="default"
                )
            else:
                response = await self.llm.client.messages.create(**request)
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Anthropic {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"Anthropic unreachable: {exc}") from exc

        usage = response.usage
        tokens = {"tokens_in": usage.input_tokens or 0, "tokens_out": usage.output_tokens or 0}

        if response.stop_reason == "refusal":
            return Reply(text="", stop="refusal", **tokens)

        self.messages.append({"role": "assistant", "content": response.content})

        text = "".join(block.text for block in response.content if block.type == "text")
        calls = [
            ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
            for block in response.content
            if block.type == "tool_use"
        ]

        return Reply(text=text, tool_calls=calls, stop=response.stop_reason or "end_turn", **tokens)


class AnthropicLLM(LLM):
    provider = "anthropic"

    def __init__(self, model: str, api_key: str | None, max_tokens: int) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else anthropic.AsyncAnthropic()

    def conversation(self, system: str, prompt: str, tools: list[ToolSpec]) -> AnthropicConversation:
        return AnthropicConversation(self, system, prompt, tools)
