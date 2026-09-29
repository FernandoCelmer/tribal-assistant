"""Which quest goals the agents may chase, and which quests they must leave alone."""

import re
from typing import Any

from tribal_assistant.core.agents.knowledge import BUILDING_BY_LABEL

FORBIDDEN = ("milícia", "milicia", "militia")
QUEST_CAPPED = {"wall": 3, "hide": 3}


class QuestRules:
    @staticmethod
    def text(quest: dict[str, Any]) -> str:
        goals = " ".join(f"{g.get('title', '')} {g.get('text', '')}" for g in quest.get("goals", []))
        return f"{quest.get('title', '')} {goals}".lower()

    @classmethod
    def forbidden(cls, quest: dict[str, Any]) -> bool:
        text = cls.text(quest)
        return any(word in text for word in FORBIDDEN)

    @staticmethod
    def goal_building(text: str) -> tuple[str, int] | None:
        """The building named first in the goal ("Construa Muralha no edifício principal" is the wall)."""
        text = text.lower()
        hits = [(text.find(label), -len(label), building) for label, building in BUILDING_BY_LABEL.items() if label in text]
        if not hits:
            return None

        numbers = re.findall(r"\d+", text)
        return min(hits)[2], int(numbers[-1]) if numbers else 0

    @classmethod
    def building_goals(cls, quests: list[dict[str, Any]], levels: dict[str, int]) -> list[tuple[str, int, str]]:
        """(building, level, quest title) for every open building goal the agents may build."""
        found = []
        for quest in quests:
            if cls.forbidden(quest):
                continue

            for goal in quest.get("goals", []):
                mapped = cls.goal_building(f"{goal.get('title', '')} {goal.get('text', '')}")
                if not mapped:
                    continue

                building, level = mapped[0], mapped[1] or int(goal.get("target") or 1)
                if level > QUEST_CAPPED.get(building, 99) or levels.get(building, 0) >= level:
                    continue

                found.append((building, level, str(quest.get("title", ""))))

        return found
