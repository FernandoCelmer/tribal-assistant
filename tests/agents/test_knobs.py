from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knobs import Knobs, KnobStore, Metrics, Tuner


def test_knobs_move_the_way_their_rule_asks() -> None:
    metrics = Metrics(rounds=20, idle_queue=0.5, recruit_starved=0.4, pop_locked=0.3)
    changes = {name: value for name, value, _ in Tuner.plan(Knobs(), metrics)}

    assert changes["filler_wait_hours"] < 0.75
    assert changes["base_stock_share"] < 0.25
    assert changes["scavenge_share"] < 0.4


def test_no_change_without_enough_rounds() -> None:
    assert Tuner.plan(Knobs(), Metrics(rounds=3, idle_queue=1.0)) == []


def test_shares_never_pass_the_whole() -> None:
    assert Knobs.step("scavenge_share", 0.95, +1) == 1.0


def test_rounds_become_metrics() -> None:
    rounds = [
        {"insights": [{"text": "fila de obras: 0 ordem(ns), termina em 0.0h"}, {"text": "coleta parada: só 7 de população"}], "deferred": [{"action": "recruit_units", "why": "faltam 10 wood"}], "budget": {"stock": {"wood": 10, "clay": 20, "iron": 30}}},
        {"insights": [], "deferred": [], "budget": {"stock": {"wood": 900, "clay": 900, "iron": 900}}},
    ]
    metrics = Tuner.measure(rounds, [("choose_relic", False, "nenhuma relíquia inicial"), ("choose_relic", False, "nenhuma relíquia"), ("choose_relic", False, "nenhuma")])

    assert metrics.idle_queue == 0.5 and metrics.scavenge_idle == 0.5 and metrics.recruit_starved == 0.5 and metrics.stock_empty == 0.5
    assert metrics.nothing_to_do["choose_relic"] == 1.0


async def test_store_keeps_value_and_history(session: AsyncSession) -> None:
    store = KnobStore(session)
    await store.set("filler_wait_hours", 0.6, "fila parada")
    await session.commit()

    assert (await store.load()).get("filler_wait_hours") == 0.6
    rows = {r["name"]: r for r in await store.rows()}
    assert rows["filler_wait_hours"]["history"][0]["why"] == "fila parada"
