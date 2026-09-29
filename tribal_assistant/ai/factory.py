"""Build the configured LLM client."""

import os

from tribal_assistant.ai.abc.llm import LLM
from tribal_assistant.ai.errors import LLMError
from tribal_assistant.ai.providers.registry import PROVIDERS, Provider
from tribal_assistant.core.config import settings


class LLMFactory:
    """Turns a provider name (plus optional overrides) into a ready LLM, or None when AI is off."""

    DISABLED = ("", "none", "off")

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.name = (provider or settings.ai_provider or "none").lower()
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @property
    def configured(self) -> bool:
        return self.name == (settings.ai_provider or "").lower()

    @property
    def enabled(self) -> bool:
        return self.name not in self.DISABLED

    def build(self) -> LLM | None:
        if not self.enabled:
            return None

        spec = self._spec()
        model = self._model(spec)
        env_key = os.environ.get(spec.key_env) if spec.key_env else None
        key = self.api_key or (settings.ai_api_key if self.configured else None) or env_key
        url = self.base_url or (settings.ai_base_url if self.configured else None) or spec.base_url

        if spec.key_env and not key:
            raise LLMError(f"sem chave para {self.name}: defina AI_API_KEY ou {spec.key_env}")

        try:
            if spec.kind == "anthropic":
                from tribal_assistant.ai.providers.anthropic import AnthropicLLM

                return AnthropicLLM(model, key, settings.ai_max_tokens)

            from tribal_assistant.ai.providers.openai_compatible import OpenAICompatibleLLM

            return OpenAICompatibleLLM(self.name, model, key, url, settings.ai_max_tokens)
        except ImportError as exc:
            raise LLMError(f"SDK do provedor {self.name} não encontrado: rode poetry install") from exc

    def _spec(self) -> Provider:
        spec = PROVIDERS.get(self.name)
        if spec is None:
            raise LLMError(f"provedor de IA desconhecido: {self.name}; use {', '.join(PROVIDERS)}")

        return spec

    def _model(self, spec: Provider) -> str:
        model = self.model or (settings.ai_model if self.configured else None) or spec.default_model
        if not model:
            raise LLMError(f"defina AI_MODEL para o provedor {self.name}")

        return model
