"""Deterministic brain: each agent's fallback policy."""

from typing import TYPE_CHECKING

from tribal_assistant.core.agents.brains.base import Brain

if TYPE_CHECKING:
    from tribal_assistant.core.agents.roles.base import VillageAgent
    from tribal_assistant.core.agents.toolbox import Toolbox


class RuleBrain(Brain):
    name = "rules"

    async def act(self, agent: "VillageAgent", box: "Toolbox") -> str:
        if box.trace is not None:
            await box.trace.step("info", f"{agent.title} decidindo por regras fixas")

        return await agent.rules(box)
