import httpx

from tribal_assistant.core.ai.providers.vertex import GeminiSchema, VertexLLM
from tribal_assistant.core.ai.types import ToolResult, ToolSpec


def test_schema_keeps_only_what_gemini_accepts() -> None:
    schema = {
        "type": "object",
        "properties": {"amount": {"type": "integer", "minimum": 100, "multipleOf": 100}, "coords": {"type": "string", "pattern": "^\\d+$"}},
        "required": ["amount"],
        "additionalProperties": False,
    }
    assert GeminiSchema.of(schema) == {"type": "object", "properties": {"amount": {"type": "integer", "minimum": 100}, "coords": {"type": "string"}}, "required": ["amount"]}


async def test_tool_call_round_trip(monkeypatch) -> None:
    replies = iter(
        [
            {"candidates": [{"content": {"role": "model", "parts": [{"functionCall": {"name": "get_forecast", "args": {"village_id": 1}}, "thoughtSignature": "x"}]}, "finishReason": "STOP"}], "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 2}},
            {"candidates": [{"content": {"role": "model", "parts": [{"text": "pronto"}]}, "finishReason": "STOP"}]},
        ]
    )
    sent: list[dict] = []

    async def fake_post(self, url, params=None, json=None):
        sent.append(json)
        return httpx.Response(200, json=next(replies), request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    llm = VertexLLM("gemini-2.5-flash", "k", "https://example/models", 256)
    chat = llm.conversation("sistema", "oi", [ToolSpec("get_forecast", "previsão", {"type": "object", "properties": {"village_id": {"type": "integer"}}})])

    first = await chat.send()
    assert first.tool_calls[0].name == "get_forecast" and first.tokens_in == 10

    second = await chat.send([ToolResult(first.tool_calls[0].id, "armazém enche em 3h")])
    assert second.text == "pronto"
    assert sent[1]["contents"][2]["parts"][0]["functionResponse"]["name"] == "get_forecast"
    assert sent[1]["contents"][1]["parts"][0]["thoughtSignature"] == "x"
