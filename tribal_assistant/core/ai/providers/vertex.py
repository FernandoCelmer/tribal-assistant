"""Gemini on Vertex AI with an API key (express mode): native generateContent with function calling."""

from typing import Any

import httpx

from tribal_assistant.core.ai.abc.llm import LLM, Conversation
from tribal_assistant.core.ai.errors import LLMError
from tribal_assistant.core.ai.types import Reply, ToolCall, ToolResult, ToolSpec

SCHEMA_KEYS = {"type", "description", "enum", "items", "properties", "required", "minimum", "maximum", "minItems", "maxItems", "nullable", "format"}
TIMEOUT = 120


class GeminiSchema:
    """JSON Schema reduced to the OpenAPI subset Gemini accepts for function parameters."""

    @classmethod
    def of(cls, schema: Any) -> Any:
        if isinstance(schema, list):
            return [cls.of(item) for item in schema]

        if not isinstance(schema, dict):
            return schema

        clean: dict[str, Any] = {}
        for key, value in schema.items():
            if key not in SCHEMA_KEYS:
                continue
            if key == "properties":
                clean[key] = {name: cls.of(prop) for name, prop in value.items()}
            elif key == "items":
                clean[key] = cls.of(value)
            elif key == "type" and isinstance(value, list):
                kinds = [kind for kind in value if kind != "null"]
                clean[key] = kinds[0] if kinds else "string"
                clean["nullable"] = "null" in value
            else:
                clean[key] = value

        if clean.get("type") == "object" and not clean.get("properties"):
            clean.pop("required", None)
        return clean


class VertexConversation(Conversation):
    def __init__(self, llm: "VertexLLM", system: str, prompt: str, tools: list[ToolSpec]) -> None:
        self.llm = llm
        self.system = system
        self.tools = [
            {"functionDeclarations": [{"name": t.name, "description": t.description, "parameters": GeminiSchema.of(t.parameters)} for t in tools]}
        ] if tools else []
        self.contents: list[dict[str, Any]] = [{"role": "user", "parts": [{"text": prompt}]}]
        self.names: dict[str, str] = {}

    async def send(self, results: list[ToolResult] | None = None) -> Reply:
        if results:
            self.contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": self.names.get(r.call_id, r.call_id),
                                "response": {"error" if r.is_error else "result": r.content},
                            }
                        }
                        for r in results
                    ],
                }
            )

        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": self.system}]},
            "contents": self.contents,
            "generationConfig": {"maxOutputTokens": self.llm.max_tokens},
        }
        if self.tools:
            body["tools"] = self.tools

        data = await self.llm.generate(body)
        candidate = (data.get("candidates") or [{}])[0]
        content = candidate.get("content") or {"role": "model", "parts": []}
        content.setdefault("role", "model")
        self.contents.append(content)

        texts, calls = [], []
        for part in content.get("parts", []):
            if "text" in part and not part.get("thought"):
                texts.append(part["text"])
            if "functionCall" in part:
                call_id = f"call_{len(self.names) + 1}"
                self.names[call_id] = part["functionCall"]["name"]
                calls.append(ToolCall(id=call_id, name=part["functionCall"]["name"], arguments=part["functionCall"].get("args") or {}))

        usage = data.get("usageMetadata") or {}
        return Reply(
            text="".join(texts),
            tool_calls=calls,
            stop="tool_use" if calls else str(candidate.get("finishReason") or "stop").lower(),
            tokens_in=int(usage.get("promptTokenCount") or 0),
            tokens_out=int(usage.get("candidatesTokenCount") or 0),
        )


class VertexLLM(LLM):
    def __init__(self, model: str, api_key: str | None, base_url: str, max_tokens: int) -> None:
        self.provider = "vertex"
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens

    async def generate(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{self.model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(url, params={"key": self.api_key}, json=body)
        except httpx.HTTPError as exc:
            raise LLMError(f"vertex inacessível: {exc}") from exc

        if response.status_code >= 400:
            try:
                message = response.json().get("error", {}).get("message", response.text)
            except ValueError:
                message = response.text
            raise LLMError(f"vertex {response.status_code}: {message[:300]}")

        return response.json()

    def conversation(self, system: str, prompt: str, tools: list[ToolSpec]) -> VertexConversation:
        return VertexConversation(self, system, prompt, tools)
