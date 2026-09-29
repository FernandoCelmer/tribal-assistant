"""Game facts from the official help pages and the strategy guides."""

from typing import Any

from tribal_assistant.core.agents.knowledge import GameKnowledge
from tribal_assistant.core.errors import NotFoundError


class KnowledgeService:
    def strategy(self) -> str:
        return GameKnowledge.strategy

    def buildings(self) -> dict[str, Any]:
        return {key: GameKnowledge.building(key) for key in GameKnowledge.buildings}

    def building(self, key: str) -> dict[str, Any]:
        info = GameKnowledge.building(key)
        if info is None:
            raise NotFoundError(f"edifício {key!r} desconhecido")

        return info

    def units(self) -> dict[str, Any]:
        return {key: GameKnowledge.unit(key) for key in GameKnowledge.units}

    def unit(self, key: str) -> dict[str, Any]:
        info = GameKnowledge.unit(key)
        if info is None:
            raise NotFoundError(f"unidade {key!r} desconhecido")

        return info

    def guide(self, name: str) -> str:
        text = GameKnowledge.guide(name)
        if text is None:
            raise NotFoundError(f"guia {name!r} desconhecido; use {', '.join(GameKnowledge.guides)}")

        return text
