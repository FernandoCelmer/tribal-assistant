"""Learns the smallest squad the world accepts from the game's own refusal message."""

import math
import re

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knobs import KnobStore

MIN_POP = re.compile(r"pelo menos (\d+)(?: de)? população", re.I)
UNIT_POP = {"spear": 1, "sword": 1, "axe": 1, "archer": 1, "spy": 2, "light": 4, "marcher": 5, "heavy": 6, "ram": 5, "catapult": 8, "knight": 10, "snob": 100}


class MinimumSquad:
    def __init__(self, session: AsyncSession) -> None:
        self.store = KnobStore(session)
        self.session = session

    async def learn(self, knob_name: str, population: int, per_unit: int) -> int:
        """Raise the knob to the units that reach the population the game asked for; never lowers it."""
        needed = math.ceil(population / max(1, per_unit))
        current = (await self.store.load()).int(knob_name)
        if needed > current:
            await self.store.set(knob_name, needed, f"o jogo pediu pelo menos {population} de população por envio")
            await self.session.commit()
        return max(needed, current)
