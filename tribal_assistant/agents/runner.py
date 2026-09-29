"""One round of every specialist on every own village."""

import asyncio
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from loguru import logger

from tribal_assistant.agents.brains.base import Brain
from tribal_assistant.agents.brains.llm import LLMBrain
from tribal_assistant.agents.brains.rules import RuleBrain
from tribal_assistant.agents.context import ContextLoader
from tribal_assistant.agents.learning import LessonBook
from tribal_assistant.agents.roles.base import VillageAgent
from tribal_assistant.agents.roles.commander import CommanderAgent
from tribal_assistant.agents.roles.economist import EconomistAgent
from tribal_assistant.agents.roles.quartermaster import QuartermasterAgent
from tribal_assistant.agents.roles.raider import RaiderAgent
from tribal_assistant.agents.roles.steward import StewardAgent
from tribal_assistant.agents.roles.strategist import StrategistAgent
from tribal_assistant.agents.toolbox import Toolbox
from tribal_assistant.agents.trace import RunTrace
from tribal_assistant.ai.errors import LLMError
from tribal_assistant.ai.factory import LLMFactory
from tribal_assistant.client.actions import GameActions
from tribal_assistant.db.session import SessionFactory
from tribal_assistant.repositories.agent_settings import AgentSettingsRepository
from tribal_assistant.repositories.agents import AgentRepository
from tribal_assistant.repositories.observability import ObservabilityRepository

STALE_MINUTES = 15


@dataclass
class VillageRun:
    village: str
    summaries: dict[str, str] = field(default_factory=dict)


@dataclass
class RunReport:
    run_id: str
    brain: str
    dry_run: bool
    villages: list[VillageRun] = field(default_factory=list)
    error: str | None = None


class AgentRunner:
    """Refreshes quests, runs each specialist per village in order, then re-syncs the account."""

    AGENTS: tuple[type[VillageAgent], ...] = (
        QuartermasterAgent,
        StewardAgent,
        StrategistAgent,
        EconomistAgent,
        CommanderAgent,
        RaiderAgent,
    )

    _lock = asyncio.Lock()

    def __init__(self, dry_run: bool | None = None, brain: Brain | None = None, trigger: str = "manual") -> None:
        self.dry_run = dry_run
        self.trigger = trigger
        self.brain = brain or self._default_brain()
        self.rules_brain = RuleBrain()
        self.actions = GameActions()
        self.agents = [agent() for agent in self.AGENTS]

    @staticmethod
    def _default_brain() -> Brain:
        try:
            llm = LLMFactory().build()
        except LLMError as exc:
            logger.warning("AI disabled: {}", exc)
            return RuleBrain()

        return LLMBrain(llm) if llm else RuleBrain()

    def _llm_identity(self) -> tuple[str | None, str | None]:
        llm = getattr(self.brain, "llm", None)
        return (llm.provider, llm.model) if llm else (None, None)

    async def run(self, village_ids: list[int] | None = None) -> RunReport:
        report = RunReport(run_id=uuid4().hex[:12], brain=self.brain.name, dry_run=bool(self.dry_run))

        if self._lock.locked():
            report.error = "outra rodada de agentes já está em andamento"
            return report

        async with self._lock, SessionFactory() as session:
            observability = ObservabilityRepository(session)
            await observability.interrupt_stale(older_than_minutes=STALE_MINUTES)

            active = await observability.active_run(within_minutes=STALE_MINUTES)
            if active is not None:
                report.error = f"rodada {active.run_id} ({active.trigger}) ainda em andamento em outro processo"
                logger.info("Skipping agent round: {}", report.error)
                return report

            config = await AgentSettingsRepository(session).get()
            report.dry_run = config.dry_run if self.dry_run is None else self.dry_run

            provider, model = self._llm_identity()
            trace = RunTrace(
                session,
                run_id=report.run_id,
                trigger=self.trigger,
                brain=self.brain.name,
                provider=provider,
                model=model,
                dry_run=report.dry_run,
            )
            await trace.start()
            logger.info("Agent round {} started ({}, {})", report.run_id, self.brain.name, self.trigger)

            try:
                acted = await self._round(session, trace, config, report, village_ids)
            except Exception as exc:
                logger.exception("Agent round {} failed", report.run_id)
                report.error = str(exc)
                await trace.step("error", str(exc), is_error=True)
                await trace.finish(villages=len(report.villages), status="failed", error=str(exc))
                return report

            status = "skipped" if report.error else "done"
            await trace.finish(villages=len(report.villages), status=status, error=report.error)
            logger.info(
                "Agent round {} {}: {} ok, {} refused, {} failed",
                report.run_id,
                status,
                trace.run.actions_ok,
                trace.run.actions_refused,
                trace.run.actions_failed,
            )

        if acted:
            await self._resync()

        return report

    async def _round(
        self,
        session: Any,
        trace: RunTrace,
        config: Any,
        report: RunReport,
        village_ids: list[int] | None,
    ) -> bool:
        contexts = await ContextLoader(session).load(village_ids)
        if not contexts:
            report.error = "nenhuma aldeia sincronizada; rode sync primeiro"
            await trace.step("error", report.error, is_error=True)
            return False

        trace.focus(None, "", "quartermaster")
        await trace.step("info", "lendo missões e recompensas no jogo")
        await self._refresh_quests(session, contexts[0].game_id)
        contexts = await ContextLoader(session).load(village_ids)

        acted = False

        for ctx in contexts:
            label = f"{ctx.village.name} ({ctx.village.coords})"
            village = VillageRun(village=label)

            for agent in self.agents:
                trace.focus(ctx.id, label, agent.key)
                brain = self._brain_for(agent, ctx, config)

                box = Toolbox(
                    agent=agent,
                    ctx=ctx,
                    session=session,
                    config=config,
                    run_id=report.run_id,
                    dry_run=report.dry_run,
                    actions=self.actions,
                    trace=trace,
                )
                box.brain_name = brain.name
                summary = await brain.act(agent, box)

                await trace.step("summary", summary)
                await box.note(summary)

                village.summaries[agent.key] = summary
                acted = acted or box.acted

            report.villages.append(village)

        return acted

    def _brain_for(self, agent: VillageAgent, ctx: Any, config: Any) -> Brain:
        if not isinstance(self.brain, LLMBrain):
            return self.rules_brain

        if agent.key not in config.llm_agents or not agent.needs_llm(ctx, config):
            return self.rules_brain

        self.brain.max_steps = config.llm_max_steps
        return self.brain

    async def _refresh_quests(self, session, game_id: str) -> None:
        if not game_id:
            return

        try:
            quests, rewards = await self.actions.read_quests(game_id)
        except Exception as exc:
            logger.warning("Could not read quests: {}", exc)
            return

        await AgentRepository(session).save_quests(quests, rewards)

        book = LessonBook(session)
        for quest in quests:
            await book.quest(quest.quest_id, quest.title, quest.state, [asdict(g) for g in quest.goals], quest.description)

        await session.commit()

    @staticmethod
    async def _resync() -> None:
        from tribal_assistant.client.modules.game_sync import sync_game

        try:
            await sync_game()
        except Exception as exc:
            logger.warning("Post-run sync failed: {}", exc)
