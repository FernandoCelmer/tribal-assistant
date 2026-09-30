"""Short texts the game asks for (profile), written by the configured model from the account's own data."""

import json
from typing import Any

from loguru import logger

from tribal_assistant.core.ai.errors import LLMError
from tribal_assistant.core.ai.factory import LLMFactory

MAX_CHARS = 500

SYSTEM = (
    "Você escreve o texto de perfil de um jogador de Tribal Wars (servidor brasileiro), em português, "
    "em primeira pessoa, com 2 a 4 frases curtas e naturais. Use só os fatos informados; não invente conquistas, "
    "números ou alianças. Sem links, sem contato externo, sem emojis, sem hashtags. Responda só com o texto."
)


class ModelWriter:
    """Asks the configured model for one text; None whenever the model is off or fails."""

    def __init__(self, factory: LLMFactory | None = None) -> None:
        self.factory = factory or LLMFactory()

    async def ask(self, system: str, prompt: str, purpose: str) -> str | None:
        try:
            llm = self.factory.build()
        except LLMError as exc:
            logger.warning("Sem IA para escrever {}: {}", purpose, exc)
            return None

        if llm is None:
            return None

        try:
            reply = await llm.conversation(system, prompt, []).send()
        except LLMError as exc:
            logger.warning("IA não escreveu {}: {}", purpose, exc)
            return None

        return reply.text


class ProfileWriter(ModelWriter):
    @staticmethod
    def facts(player: dict[str, Any] | None, villages: int, role: str, tribe: str | None) -> str:
        player = player or {}
        return json.dumps(
            {
                "nome": player.get("name"),
                "mundo": player.get("world"),
                "pontos": player.get("points"),
                "ranking": player.get("rank"),
                "aldeias": villages,
                "foco_atual": role,
                "tribo": tribe,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def clean(text: str) -> str | None:
        text = " ".join(text.replace('"', "").split()).strip()
        if len(text) < 10:
            return None
        return text[:MAX_CHARS]

    async def write(self, facts: str) -> str | None:
        reply = await self.ask(SYSTEM, f"Dados do jogador: {facts}\nEscreva o texto do perfil.", "o perfil")
        return self.clean(reply) if reply is not None else None
