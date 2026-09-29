"""Challenges read from the achievements screen, with the plan the agents follow for each."""

import json
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.challenges import ChallengePlan
from tribal_assistant.core.agents.learning import CHALLENGES
from tribal_assistant.core.repositories.lessons import LessonRepository
from tribal_assistant.core.schemas.challenges import ChallengeOut, ChallengesOut


class ChallengeService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = LessonRepository(session)

    async def list(self) -> ChallengesOut:
        row = await self.repo.get(CHALLENGES)
        raw = json.loads(row.data).get("items", []) if row else []
        items = [ChallengeOut(**ChallengePlan.enrich(item)) for item in raw]
        summary = Counter("done" if i.done else i.status for i in items)
        return ChallengesOut(updated_at=row.last_seen if row else None, items=items, summary=dict(summary))
