import pytest

from tribal_assistant.core.ai.abc.llm import LLM
from tribal_assistant.core.ai.errors import LLMError
from tribal_assistant.core.ai.factory import LLMFactory
from tribal_assistant.core.config import settings


@pytest.mark.parametrize(
    ("provider", "kind", "base_url"),
    [
        ("anthropic", "AnthropicLLM", None),
        ("openai", "OpenAICompatibleLLM", None),
        ("grok", "OpenAICompatibleLLM", "https://api.x.ai/v1"),
        ("gemini", "OpenAICompatibleLLM", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    ],
)
def test_providers_build_llms(provider: str, kind: str, base_url: str | None) -> None:
    llm = LLMFactory(provider, api_key="test").build()

    assert isinstance(llm, LLM)
    assert type(llm).__name__ == kind
    if base_url:
        assert str(llm.client.base_url).rstrip("/") == base_url.rstrip("/")


def test_ollama_needs_no_key() -> None:
    assert LLMFactory("ollama").build() is not None


def test_disabled_and_invalid_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_api_key", None)
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    assert LLMFactory("none").build() is None

    with pytest.raises(LLMError, match="desconhecido"):
        LLMFactory("nope").build()

    with pytest.raises(LLMError, match="sem chave"):
        LLMFactory("grok", api_key=None).build()
