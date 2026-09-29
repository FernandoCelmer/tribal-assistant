from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import context, unit
from tribal_assistant.agents.roles.commander import CommanderAgent
from tribal_assistant.agents.roles.economist import EconomistAgent
from tribal_assistant.agents.roles.quartermaster import QuartermasterAgent
from tribal_assistant.agents.roles.raider import RaiderAgent
from tribal_assistant.agents.roles.strategist import StrategistAgent
from tribal_assistant.agents.toolbox import Toolbox
from tribal_assistant.client.actions import ActionResult
from tribal_assistant.models.village import Village
from tribal_assistant.models.world import WorldVillage
from tribal_assistant.repositories.agents import AgentRepository
from tribal_assistant.schemas.agent_settings import AgentSettings


class FakeActions:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def upgrade_building(self, village_id: str, building: str, finish_free: bool = True) -> ActionResult:
        self.calls.append(("upgrade", building))
        return ActionResult(True, "upgrade_building", f"{building} na fila")

    async def recruit(self, village_id: str, unit: str, count: int) -> ActionResult:
        self.calls.append(("recruit", unit, count))
        return ActionResult(True, "recruit", f"{count} {unit}", {"count": count})

    async def send_attack(self, village_id: str, x: int, y: int, units: dict) -> ActionResult:
        self.calls.append(("attack", f"{x}|{y}", units))
        return ActionResult(True, "send_attack", "enviado")

    async def claim_rewards(self, village_id: str) -> ActionResult:
        self.calls.append(("claim",))
        return ActionResult(True, "claim_rewards", "2 recompensas")

    async def complete_quest(self, village_id: str, quest_id: str) -> ActionResult:
        self.calls.append(("complete", quest_id))
        return ActionResult(True, "complete_quest", "ok")


def _box(session: AsyncSession, agent, ctx, *, dry_run: bool = False, actions: FakeActions | None = None) -> Toolbox:
    return Toolbox(
        agent=agent,
        ctx=ctx,
        session=session,
        config=AgentSettings(),
        run_id="test",
        dry_run=dry_run,
        actions=actions or FakeActions(),
    )


async def test_agent_cannot_build_outside_its_area(session: AsyncSession) -> None:
    box = _box(session, EconomistAgent(), context())

    outcome = await box.invoke("upgrade_building", {"building": "barracks", "reason": "x"})

    assert not outcome.ok
    assert "área" in outcome.text


async def test_tool_not_in_role_is_unavailable(session: AsyncSession) -> None:
    box = _box(session, EconomistAgent(), context())

    outcome = await box.invoke("send_farm_attack", {"target": "1|1", "units": {"spear": 1}, "reason": "x"})

    assert not outcome.ok
    assert "não disponível" in outcome.text


async def test_dry_run_records_without_touching_the_game(session: AsyncSession) -> None:
    actions = FakeActions()
    ctx = context()
    box = _box(session, EconomistAgent(), ctx, dry_run=True, actions=actions)

    outcome = await box.invoke("upgrade_building", {"building": "wood", "reason": "missão"})

    assert outcome.ok and "simulação" in outcome.text
    assert actions.calls == []
    assert ctx.stock["wood"] == 900

    decision = (await AgentRepository(session).decisions(limit=1))[0]
    assert decision.action == "upgrade_building" and decision.dry_run and decision.reason == "missão"


async def test_rule_agents_act_through_guardrails(session: AsyncSession) -> None:
    session.add_all(
        [
            Village(id=1, game_id="105765", name="Aldeia", coords="500|500", is_own=True),
            WorldVillage(id=9, name="Bárbara", x=503, y=500, player_id=0, points=30),
        ]
    )
    await session.commit()

    actions = FakeActions()
    quests = [{"id": "1040", "title": "Q", "state": "progress", "can_complete": True,
               "goals": [{"title": "Melhore Bosque", "text": "Expanda Bosque ao nível 5.", "current": 4, "target": 5}]}]
    ctx = context(units=[unit("spear", 10)], quests=quests, rewards=2)

    for agent in (QuartermasterAgent(), StrategistAgent(), EconomistAgent(), CommanderAgent(), RaiderAgent()):
        await agent.rules(_box(session, agent, ctx, actions=actions))

    kinds = [call[0] for call in actions.calls]
    assert kinds[:2] == ["complete", "claim"]
    assert ("upgrade", "wood") in actions.calls
    assert any(call[0] == "recruit" for call in actions.calls)
    assert ("attack", "503|500", {"spear": 10}) in actions.calls
    assert next(s.target for s in ctx.plan if s.kind == "build") == "wood"
