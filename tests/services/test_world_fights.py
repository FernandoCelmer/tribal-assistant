from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import context
from tribal_assistant.core.agents.coordination.threat import ThreatScan
from tribal_assistant.core.game.world import WorldData, parse_conquests, parse_kills
from tribal_assistant.core.models.world import WorldCombat
from tribal_assistant.core.repositories.world import WorldRepository


def data(attack: dict[int, int], conquests: list[dict] | None = None) -> WorldData:
    villages = [{"id": 1, "name": "A", "x": 500, "y": 500, "player_id": 0, "points": 100, "bonus_id": 0},
                {"id": 2, "name": "B", "x": 503, "y": 500, "player_id": 77, "points": 90, "bonus_id": 0}]
    players = [{"id": 77, "name": "Doris", "ally_id": 0, "villages": 1, "points": 90, "rank": 1}]
    return WorldData(villages, players, [], {}, attack, {77: 5}, conquests or [])


def test_parse_fight_files() -> None:
    assert parse_kills("1,920063764,973991\n2,7148381,775276\n") == {920063764: 973991, 7148381: 775276}
    (conquest,) = parse_conquests("403,1787923909,919706271,0\n")
    assert conquest["village_id"] == 403 and conquest["new_owner"] == 919706271 and conquest["at"].year == 2026


async def test_sync_keeps_how_much_each_player_attacked_since_the_last_one(session: AsyncSession) -> None:
    repo = WorldRepository(session)
    await repo.replace(data({77: 100}))
    await repo.replace(data({77: 160}))

    row = (await session.execute(select(WorldCombat))).scalar_one()
    assert (row.attack, row.attack_gain) == (160, 60) and row.attacked_at is not None


async def test_a_weak_neighbour_who_attacks_or_conquers_is_a_threat(session: AsyncSession) -> None:
    repo = WorldRepository(session)
    recent = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
    await repo.replace(data({77: 100}))
    await repo.replace(data({77: 130}, [{"village_id": 2, "at": recent, "new_owner": 77, "old_owner": 0}]))

    scan = ThreatScan(session)
    threats = await scan.near(context())

    assert threats[0].attacking and threats[0].conquests == 1
    assert scan.dangerous(threats, own_points=5000) == threats
    assert "derrotou 130 atacando" in ThreatScan.summary(threats)
