from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.coordination.policy import Policy
from tribal_assistant.core.agents.knobs import Knobs, KnobStore, Metrics, Tuner
from tribal_assistant.core.agents.pacing import BuildPacing
from tribal_assistant.core.agents.proposers.raid import RaidPlanner


def test_knobs_move_the_way_their_rule_asks() -> None:
    metrics = Metrics(rounds=20, idle_queue=0.5, recruit_starved=0.4, pop_locked=0.3)
    changes = {name: value for name, value, _ in Tuner.plan(Knobs(), metrics)}

    assert changes["filler_wait_hours"] < 0.75
    assert changes["base_stock_share"] < 0.25
    assert changes["scavenge_share"] < 0.4


def test_no_change_without_enough_rounds() -> None:
    assert Tuner.plan(Knobs(), Metrics(rounds=3, idle_queue=1.0)) == []


def test_a_knob_is_judged_only_by_rounds_after_its_last_change() -> None:
    start = datetime(2026, 10, 1, 12, 0)

    assert Tuner.since(None, start) == start
    assert Tuner.since(datetime(2026, 10, 1, 9, 0), start) == start
    assert Tuner.since(datetime(2026, 10, 1, 13, 47, 31), start) == datetime(2026, 10, 1, 13, 40)


def test_plan_moves_only_the_knobs_of_its_group() -> None:
    metrics = Metrics(rounds=5, idle_queue=0.5, recruit_starved=0.4)
    changes = {name for name, _, _ in Tuner.plan(Knobs(), metrics, {"filler_wait_hours"}, least=4)}

    assert changes == {"filler_wait_hours"}


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


def test_every_knob_starts_positive_and_shares_stay_within_the_whole() -> None:
    for name, spec in Knobs.SPECS.items():
        assert spec.default > 0, name
        if spec.share:
            assert spec.default <= 1.0, name


def test_policy_limits_come_from_the_knobs_and_emergency_never_raids() -> None:
    knobs = Knobs({"policy.offensive.attack_radius": 20, "policy.offensive.recruit_budget": 0.5, "policy.emergency.recruit_budget": 0.6})
    offensive = Policy.for_role("offensive", knobs)
    emergency = Policy.for_role("emergency", knobs)

    assert offensive.attack_radius == 20 and offensive.recruit_budget == 0.5 and offensive.knobs is knobs
    assert Policy.for_role("unknown").max_attacks_per_hour == 12
    assert emergency.max_attacks_per_hour == 0 and emergency.attack_radius == 0 and emergency.recruit_budget == 0.6


def test_lost_raids_tighten_the_raiding_knobs() -> None:
    changes = {name: value for name, value, _ in Tuner.plan(Knobs(), Metrics(rounds=20, raids_lost=0.5))}

    assert changes["raid.min_confidence"] > 0.35
    assert changes["raid.radius_cavalry"] < 10
    assert changes["policy.growth.attack_radius"] < 12
    assert changes["policy.offensive.max_attacks_per_hour"] < 30
    assert changes["raid.wall_light_factor"] > 1.0


def test_full_storage_spends_sooner_and_threats_raise_the_defense_goals() -> None:
    changes = {name: value for name, value, _ in Tuner.plan(Knobs(), Metrics(rounds=20, storage_full=0.5, threatened=0.3))}

    assert changes["recruit.batch"] > 25
    assert changes["storage.near_full_share"] < 0.85
    assert changes["iron_parking.full_share"] < 0.85
    assert changes["defense.wall_target"] > 8 and changes["defense.prepare_hours"] > 72


def test_cooldowns_follow_what_the_checks_find() -> None:
    idle = Metrics(rounds=20, nothing_to_do={"craft_event_item": 0.9, "research_unit": 0.0})
    changes = {name: value for name, value, _ in Tuner.plan(Knobs(), idle)}

    assert changes["cooldown.forge"] > 3
    assert changes["cooldown.smith"] < 1


def test_calm_windows_walk_a_knob_back_to_its_default_without_passing_it() -> None:
    changes = {name: value for name, value, _ in Tuner.plan(Knobs({"raid.min_infantry": 12, "defense.wall_target": 9}), Metrics(rounds=20))}

    assert changes["raid.min_infantry"] == 10
    assert changes["defense.wall_target"] == 8
    assert Knobs.toward("farm.lead_hours", 1.1, 0) == 1.0
    assert Knobs.toward("farm.lead_hours", 1.0, 0) == 1.0


def test_new_metrics_come_from_rounds_and_decisions() -> None:
    rounds = [
        {"insights": [{"text": "ataque de x: hold (defesa; nenhuma bárbara no raio longe o bastante para esquivar)"}], "deferred": [{"action": "upgrade_building", "why": "faltam 120 iron"}, {"action": "use_item", "why": "limite de ações por rodada"}]},
        {"insights": [], "deferred": []},
    ]
    decisions = [("send_farm_attack", False, "limite de 12 ataques por hora atingido"), ("send_spy", True, "enviado")]
    metrics = Tuner.measure(rounds, decisions)

    assert metrics.iron_short == 0.5 and metrics.actions_capped == 0.5 and metrics.dodge_stuck == 0.5
    assert metrics.raids_capped == 0.5


def test_pure_planners_read_the_knobs_they_are_given() -> None:
    wider = Knobs({"raid.radius_infantry": 6, "raid.max_cap": 20})
    assert RaidPlanner.in_range("spear", 5, wider) and not RaidPlanner.in_range("spear", 5)
    assert RaidPlanner.max_raids(1000, 30, 0, wider) == 20
    assert BuildPacing.pit_caps({"wood": 6, "stone": 6}, Knobs({"pacing.iron_gap": 1}))["iron"] == 5


async def test_tuner_runs_once_per_interval_even_across_restarts(session: AsyncSession) -> None:
    assert await Tuner(session).due()
    await Tuner(session).run()

    assert not await Tuner(session).due()
    assert await Tuner(session).run() == []
    assert await Tuner(session).run(force=True) == []


def test_a_knob_that_keeps_moving_without_effect_returns_to_default() -> None:
    default = Knobs.SPECS["filler_wait_hours"].default
    walk = [{"at": "2026-10-01T10:00", "from": 1.0, "to": 0.85, "why": "fila"}] * 6

    value, why, blocked = Tuner.brake("filler_wait_hours", 0.4, 0.34, "fila parada", walk, Knobs())

    assert value == default and blocked == -1 and "sem resolver" in why


def test_a_shut_direction_stays_shut() -> None:
    now = datetime.now().isoformat(timespec="minutes")
    shut = [{"at": now, "from": 0.4, "to": 0.75, "why": "x", "blocked": -1}]

    assert Tuner.brake("filler_wait_hours", 0.75, 0.6, "fila parada", shut, Knobs()) is None
    assert Tuner.brake("filler_wait_hours", 0.75, 0.9, "outra", shut, Knobs())[0] == 0.9


def test_recruits_by_the_routine_between_rounds_count_as_recruiting() -> None:
    start = datetime(2026, 10, 2, 8, 0)
    rounds = [(1, start + timedelta(minutes=m)) for m in (0, 10, 20, 30)]
    recruits = [(1, start + timedelta(minutes=15)), (1, start + timedelta(minutes=29))]

    assert Tuner.stalled(rounds, recruits) == 0.5


def test_offers_taken_within_minutes_count_as_snapped() -> None:
    start = datetime(2026, 10, 2, 8, 0, 30)
    made = [start, start + timedelta(hours=1), start + timedelta(hours=2)]
    taken = [datetime(2026, 10, 2, 8, 0), datetime(2026, 10, 2, 9, 5)]

    assert Tuner.snapped(made, taken) == 0.667


def test_the_ask_ratio_rises_when_offers_go_fast_and_falls_when_they_wait() -> None:
    fast = {n for n, _, _ in Tuner.plan(Knobs(), Metrics(rounds=20, offers_made=5, offers_snapped=0.9))}
    slow = {n: v for n, v, _ in Tuner.plan(Knobs(), Metrics(rounds=20, offers_made=5, offers_snapped=0.1))}

    assert "market.ask_ratio" in fast
    assert slow["market.ask_ratio"] < 1.0
