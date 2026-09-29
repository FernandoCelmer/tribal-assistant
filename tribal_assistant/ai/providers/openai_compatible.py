"""Any OpenAI-compatible Chat Completions endpoint: OpenAI, Grok (xAI), Gemini, Ollama, vLLM, LM Studio."""

import json
from typing import Any

from tribal_assistant.ai.abc.llm import LLM, Conversation
from tribal_assistant.ai.errors import LLMError
from tribal_assistant.ai.types import Reply, ToolCall, ToolResult, ToolSpec


class OpenAICompatibleConversation(Conversation):
    def __init__(
        self, llm: "OpenAICompatibleLLM", system: str, prompt: str, tools: list[ToolSpec]
    ) -> None:
        self.llm = llm
        self.tools = [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
            }
            for t in tools
        ]
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

    async def send(self, results: list[ToolResult] | None = None) -> Reply:
        import openai

        for result in results or []:
            content = f"ERRO: {result.content}" if result.is_error else result.content
            self.messages.append({"role": "tool", "tool_call_id": result.call_id, "content": content})

        try:
            response = await self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=self.messages,
                tools=self.tools or openai.NOT_GIVEN,
                max_tokens=self.llm.max_tokens,
            )
        except openai.APIStatusError as exc:
            raise LLMError(f"{self.llm.provider} {exc.status_code}: {exc.message}") from exc
        except openai.APIConnectionError as exc:
            raise LLMError(f"{self.llm.provider} unreachable: {exc}") from exc

        choice = response.choices[0]
        message = choice.message
        self.messages.append(message.model_dump(exclude_none=True))

        calls = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"_invalid_json": call.function.arguments}
            calls.append(ToolCall(id=call.id, name=call.function.name, arguments=arguments))

        usage = response.usage

        return Reply(
            text=message.content or "",
            tool_calls=calls,
            stop=choice.finish_reason or "stop",
            tokens_in=(usage.prompt_tokens or 0) if usage else 0,
            tokens_out=(usage.completion_tokens or 0) if usage else 0,
        )


class OpenAICompatibleLLM(LLM):
    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str | None,
        base_url: str | None,
        max_tokens: int,
    ) -> None:
        import openai

        self.provider = provider
        self.model = model
        self.max_tokens = max_tokens
        self.client = openai.AsyncOpenAI(api_key=api_key or "not-needed", base_url=base_url)

    def conversation(
        self, system: str, prompt: str, tools: list[ToolSpec]
    ) -> OpenAICompatibleConversation:
        return OpenAICompatibleConversation(self, system, prompt, tools)
