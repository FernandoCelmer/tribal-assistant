"""Known LLM providers: SDK kind, endpoint, key variable and default model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    kind: str
    base_url: str | None
    key_env: str | None
    default_model: str | None


PROVIDERS = {
    "anthropic": Provider("anthropic", None, "ANTHROPIC_API_KEY", "claude-opus-5"),
    "openai": Provider("openai", None, "OPENAI_API_KEY", "gpt-5"),
    "grok": Provider("openai", "https://api.x.ai/v1", "XAI_API_KEY", "grok-4.20-0309-non-reasoning"),
    "gemini": Provider(
        "openai",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "GEMINI_API_KEY",
        "gemini-2.5-pro",
    ),
    "ollama": Provider("openai", "http://localhost:11434/v1", None, "llama3.1"),
    "openai-compatible": Provider("openai", None, "OPENAI_API_KEY", None),
}
