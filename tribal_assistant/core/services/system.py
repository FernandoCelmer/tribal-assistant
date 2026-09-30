"""What the app is configured with outside the database (environment), without exposing secrets."""

import os

from tribal_assistant.core.accounts.context import current_account, current_account_id
from tribal_assistant.core.ai.errors import LLMError
from tribal_assistant.core.ai.factory import LLMFactory
from tribal_assistant.core.ai.providers.registry import PROVIDERS
from tribal_assistant.core.config import settings
from tribal_assistant.core.schemas.system import AIInfo, SystemInfo
from tribal_assistant.version import __version__


class SystemService:
    def info(self) -> SystemInfo:
        account = current_account() if current_account_id() else None
        return SystemInfo(
            version=__version__,
            world_url=account.world_url if account else None,
            server=account.server if account else None,
            sync_interval_seconds=settings.sync_interval_seconds,
            world_sync_interval_minutes=settings.world_sync_interval_minutes,
            quiet_hours=settings.quiet_hours,
            headless=settings.headless,
            database=settings.database_url.split("://", 1)[0],
            log_retention_days=settings.log_retention_days,
            trace_retention_days=settings.trace_retention_days,
            ai=self.ai(),
        )

    def ai(self) -> AIInfo:
        factory = LLMFactory()
        spec = PROVIDERS.get(factory.name)
        key_env = spec.key_env if spec else None
        key = bool(settings.ai_api_key or (key_env and os.environ.get(key_env)))

        try:
            llm = factory.build()
            error = None
        except LLMError as exc:
            llm, error = None, str(exc)

        return AIInfo(
            provider=factory.name,
            model=llm.model if llm else (settings.ai_model or (spec.default_model if spec else None)),
            base_url=settings.ai_base_url or (spec.base_url if spec else None),
            key_configured=key or (spec is not None and spec.key_env is None),
            active=llm is not None,
            error=error,
        )
