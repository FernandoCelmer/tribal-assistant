"""Agent decisions, village goals and quest state."""

import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.game.scraper.quests import Quest, QuestReward
from tribal_assistant.core.models.agent import (
    AgentDecision,
    AgentGoal,
    QuestRewardState,
    QuestState,
)


class AgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        run_id: str,
        village_id: int | None,
        agent: str,
        action: str,
        arguments: dict[str, Any],
        ok: bool,
        dry_run: bool,
        reason: str,
        result: str,
    ) -> AgentDecision:
        decision = AgentDecision(
            run_id=run_id,
            village_id=village_id,
            agent=agent,
            action=action,
            arguments=json.dumps(arguments, ensure_ascii=False, default=str),
            ok=ok,
            dry_run=dry_run,
            reason=reason,
            result=result,
        )
        self.session.add(decision)
        await self.session.commit()

        return decision

    async def decisions(
        self, village_id: int | None = None, limit: int = 50, run_id: str | None = None
    ) -> Sequence[AgentDecision]:
        stmt = select(AgentDecision).order_by(AgentDecision.id.desc()).limit(limit)

        if village_id is not None:
            stmt = stmt.where(AgentDecision.village_id == village_id)
        if run_id is not None:
            stmt = stmt.where(AgentDecision.run_id == run_id)

        return (await self.session.execute(stmt)).scalars().all()

    async def attacks_since(self, village_id: int, since: datetime) -> int:
        stmt = select(func.count(AgentDecision.id)).where(
            AgentDecision.village_id == village_id,
            AgentDecision.action.in_(("send_farm_attack", "send_farm_template", "send_spy")),
            AgentDecision.ok.is_(True),
            AgentDecision.dry_run.is_(False),
            AgentDecision.created_at >= since,
        )

        return int((await self.session.execute(stmt)).scalar_one())

    async def attacked_recently(self, target: str, minutes: int) -> bool:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=minutes)
        stmt = select(AgentDecision.arguments).where(
            AgentDecision.action.in_(("send_farm_attack", "send_farm_template")),
            AgentDecision.ok.is_(True),
            AgentDecision.dry_run.is_(False),
            AgentDecision.created_at >= since,
        )

        for raw in (await self.session.execute(stmt)).scalars():
            if json.loads(raw).get("target") == target:
                return True

        return False

    async def goal(self, village_id: int) -> str | None:
        stmt = select(AgentGoal.text).where(AgentGoal.village_id == village_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def set_goal(self, village_id: int, text: str) -> None:
        row = (
            await self.session.execute(select(AgentGoal).where(AgentGoal.village_id == village_id))
        ).scalar_one_or_none()

        if row is None:
            self.session.add(AgentGoal(village_id=village_id, text=text))
        else:
            row.text = text

        await self.session.commit()

    async def save_quests(self, quests: list[Quest], rewards: list[QuestReward]) -> None:
        seen = {q.quest_id for q in quests}
        await self.session.execute(
            update(QuestState).where(QuestState.quest_id.not_in(seen)).values(active=False)
        )

        for quest in quests:
            row = (
                await self.session.execute(select(QuestState).where(QuestState.quest_id == quest.quest_id))
            ).scalar_one_or_none()
            if row is None:
                row = QuestState(quest_id=quest.quest_id)
                self.session.add(row)

            row.line_id = quest.line_id
            row.title = quest.title
            row.state = quest.state
            row.description = quest.description
            row.goals = json.dumps([asdict(g) for g in quest.goals], ensure_ascii=False)
            row.can_complete = quest.can_complete
            row.active = True

        pending = {r.reward_id for r in rewards}
        await self.session.execute(
            update(QuestRewardState).where(QuestRewardState.reward_id.not_in(pending)).values(claimed=True)
        )

        for reward in rewards:
            row = (
                await self.session.execute(
                    select(QuestRewardState).where(QuestRewardState.reward_id == reward.reward_id)
                )
            ).scalar_one_or_none()
            if row is None:
                self.session.add(QuestRewardState(reward_id=reward.reward_id, label=reward.label))
            else:
                row.label = reward.label
                row.claimed = False

        await self.session.commit()

    async def quests(self) -> Sequence[QuestState]:
        stmt = select(QuestState).where(QuestState.active.is_(True)).order_by(QuestState.line_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def pending_rewards(self) -> Sequence[QuestRewardState]:
        stmt = select(QuestRewardState).where(QuestRewardState.claimed.is_(False))
        return (await self.session.execute(stmt)).scalars().all()
