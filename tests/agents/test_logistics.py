from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import building, context
from tribal_assistant.core.agents.coordination.round import VillageRound
from tribal_assistant.core.agents.guardrails import Guardrails
from tribal_assistant.core.agents.knobs import Knobs, Tuner
from tribal_assistant.core.agents.learning import LessonBook
from tribal_assistant.core.agents.logistics import Merchants, Need, ShipmentPlanner
from tribal_assistant.core.agents.tools.act import SendResources
from tribal_assistant.core.game.actions import ActionResult, GameActions
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.schemas.agent_settings import AgentSettings
from tribal_assistant.core.schemas.plan import PlanStep

MERCHANTS = {"free": 5, "carry": 1000}


def _origin(stock: int = 3000, storage: int = 4000):
    ctx = context(buildings=[building("main", 10), building("market", 5), building("storage", 10), building("farm", 10)], stock=stock, storage=storage)
    ctx.player = {"name": "Player"}
    return ctx


def _sibling(village_id: int, coords: str, *, stock: int = 500, storage: int = 4000, buildings=None):
    ctx = context(buildings=buildings or [building("main", 5), building("market", 1)], stock=stock, storage=storage)
    ctx.village.id = village_id
    ctx.village.game_id = str(200000 + village_id)
    ctx.village.coords = coords
    ctx.village.name = f"Aldeia {village_id}"
    return ctx


async def _villages(session: AsyncSession) -> None:
    session.add_all(
        [
            Village(id=1, game_id="105765", name="Aldeia", coords="500|500", is_own=True, storage=4000, wood=3000, clay=3000, iron=3000),
            Village(id=2, game_id="200002", name="Aldeia 2", coords="505|500", is_own=True, storage=4000, wood=500, clay=500, iron=500),
            Village(id=3, game_id="300003", name="Vizinho", coords="503|503", is_own=False, storage=4000),
            Village(id=4, game_id="400004", name="Outra conta", coords="510|500", is_own=True, storage=4000, account_id=2),
            Village(id=5, game_id="200005", name="Cheia", coords="506|500", is_own=True, storage=1000, wood=800, clay=800, iron=800),
        ]
    )
    await session.commit()


async def test_shipments_only_go_to_own_villages_of_the_same_account(session: AsyncSession) -> None:
    await _villages(session)
    guard = Guardrails(session, AgentSettings())
    ctx = _origin()
    lot = {"wood": 1000, "clay": 0, "iron": 0}

    assert await guard.check_send_resources(ctx, 2, lot, MERCHANTS) is None
    assert "não é sua" in await guard.check_send_resources(ctx, 3, lot, MERCHANTS)
    assert "não é sua" in await guard.check_send_resources(ctx, 4, lot, MERCHANTS)
    assert "não é sua" in await guard.check_send_resources(ctx, 99, lot, MERCHANTS)
    assert "mesma aldeia" in await guard.check_send_resources(ctx, 1, lot, MERCHANTS)


async def test_shipments_respect_merchants_origin_floor_and_destination_storage(session: AsyncSession) -> None:
    await _villages(session)
    guard = Guardrails(session, AgentSettings())
    ctx = _origin()

    assert "comerciantes" in await guard.check_send_resources(ctx, 2, {"wood": 1000, "clay": 1000, "iron": 1000}, {"free": 2, "carry": 1000})
    assert "reserva" in await guard.check_send_resources(ctx, 2, {"wood": 2000, "clay": 0, "iron": 0}, MERCHANTS)
    assert "estouraria" in await guard.check_send_resources(ctx, 5, {"wood": 500, "clay": 0, "iron": 0}, MERCHANTS)
    assert "nenhum recurso" in await guard.check_send_resources(ctx, 2, {"wood": 0, "clay": 0, "iron": 0}, MERCHANTS)

    ctx.village.buildings = [building("main", 10)]
    assert "sem mercado" in await guard.check_send_resources(ctx, 2, {"wood": 100, "clay": 0, "iron": 0}, MERCHANTS)


class FakeMarket:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def send_resources(self, village_id: str, x: int, y: int, amounts: dict, owner: str | None = None) -> ActionResult:
        self.calls.append((village_id, f"{x}|{y}", amounts, owner))
        return ActionResult(True, "send_resources", "enviado")


async def test_send_tool_ships_through_the_market_and_spends_the_origin(session: AsyncSession) -> None:
    await _villages(session)
    ctx = _origin()
    market = FakeMarket()
    box = SimpleNamespace(ctx=ctx, dry_run=False, guard=Guardrails(session, AgentSettings()), actions=SimpleNamespace(market=market), lessons=LessonBook(session))

    refused = await SendResources().run(box, {"to_village_id": 3, "wood": 500, "clay": 0, "iron": 0, "reason": "r"})
    assert refused.text.startswith("RECUSADO") and market.calls == []

    outcome = await SendResources().run(box, {"to_village_id": 2, "wood": 500, "clay": 300, "iron": 0, "reason": "r"})
    assert outcome.ok
    assert market.calls == [("105765", "505|500", {"wood": 500, "clay": 300, "iron": 0}, "Player")]
    assert ctx.stock == {"wood": 2500, "clay": 2700, "iron": 3000}
    assert not await LessonBook(session).due("logistics:2", 1)


def test_noble_packages_come_before_a_closer_stalled_village() -> None:
    surplus = {"wood": 2000, "clay": 2000, "iron": 2000}
    stalled = Need(2, "Perto", "501|500", {"wood": 800, "clay": 800, "iron": 0}, "obra", ShipmentPlanner.STALLED, 1.0)
    noble = Need(3, "Academia", "510|500", {"wood": 3000, "clay": 3000, "iron": 3000}, "nobre", ShipmentPlanner.NOBLE, 10.0, {"wood": 1500, "clay": 3000, "iron": 3000})

    need, lot = ShipmentPlanner.choose([stalled, noble], surplus, 5000, 1000)

    assert need.village_id == 3
    assert lot["wood"] <= 1500 and sum(lot.values()) <= 5000
    assert ShipmentPlanner.choose([stalled], surplus, 5000, 1000)[1] == {"wood": 800, "clay": 800, "iron": 0}
    assert ShipmentPlanner.choose([stalled], {"wood": 0, "clay": 0, "iron": 0}, 5000, 1000) is None


def test_donor_spares_only_above_its_floor_and_its_own_next_build() -> None:
    stock = {"wood": 3500, "clay": 3500, "iron": 1000}

    assert ShipmentPlanner.surplus(stock, 4000, 1200, {"wood": 3000}, pressed=True) == {"wood": 500, "clay": 2300, "iron": 0}
    assert ShipmentPlanner.surplus(stock, 4000, 1200, {}, pressed=False) == {"wood": 0, "clay": 0, "iron": 0}
    assert Merchants.total(5) == 5 and Merchants.total(20) == 110
    assert Merchants.needed({"wood": 1001}) == 2


async def test_round_feeds_the_academy_village_from_a_full_storage(session: AsyncSession) -> None:
    await _villages(session)
    origin = _origin(stock=3800)
    academy = _sibling(2, "505|500", buildings=[building("main", 20), building("market", 10), building("snob", 1)])

    decision, insights = await VillageRound(session, AgentSettings(), "l1", True, GameActions()).run(origin, [origin, academy])

    sent = [e for e in decision.executed if e["action"] == "send_resources"]
    assert sent and sent[0]["ok"]
    assert sent[0]["arguments"]["to_village_id"] == 2
    assert 0 < sum(sent[0]["cost"].values()) <= 5000
    assert any(i.key == "logistics" for i in insights)


async def test_round_feeds_a_stalled_plan_build_but_not_a_single_village(session: AsyncSession) -> None:
    await _villages(session)
    stalled = _sibling(2, "505|500", stock=100, buildings=[building("main", 5, cost=2500), building("market", 1)])
    stalled.plan = [PlanStep(kind="build", target="main", amount=6, status="pending")]

    alone, _ = await VillageRound(session, AgentSettings(), "l2", True, GameActions()).run(_origin(stock=3800), None)
    shared, _ = await VillageRound(session, AgentSettings(), "l3", True, GameActions()).run(_origin(stock=3800), [_origin(stock=3800), stalled])

    assert not any(e["action"] == "send_resources" for e in alone.executed)
    assert any(e["action"] == "send_resources" and e["arguments"]["to_village_id"] == 2 for e in shared.executed)


def test_tuner_measures_failed_shipments_and_nobles() -> None:
    metrics = Tuner.measure([], [("send_resources", False, "x"), ("send_resources", True, ""), ("send_noble", False, "y")])

    assert metrics.shipments_failed == 0.5
    assert metrics.nobles_failed == 1.0
    assert Knobs().get("logistics.keep_share") == 0.3
