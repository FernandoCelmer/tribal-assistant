from datetime import UTC, datetime, timedelta

from tests.agents.builders import context, scavenge, unit
from tribal_assistant.core.agents.routines import Routines
from tribal_assistant.core.schemas.game import RecruitOrderOut


def test_idle_troops_go_scavenging_on_every_free_tier():
    ctx = context(units=[unit("spear", 200), unit("sword", 40)], scavenge_options=[scavenge(1), scavenge(2), scavenge(3, busy=True), scavenge(4, locked=True)])

    parts = Routines.scavenge_plan(ctx)

    assert set(parts) <= {1, 2} and parts
    assert sum(p.get("spear", 0) for p in parts.values()) > 150


def test_no_scavenging_while_an_attack_comes():
    ctx = context(units=[unit("spear", 200)], scavenge_options=[scavenge(1)])
    ctx.commands = [{"direction": "in", "kind": "attack"}]

    assert Routines.scavenge_plan(ctx) == {}


def test_recruit_batch_spends_only_a_share_of_the_stock():
    ctx = context(units=[unit("spear", 10, cost=(50, 30, 10, 1))], stock=1000, pop_free=500)

    count = Routines.recruit_count(ctx, ctx.unit("spear"))

    assert 0 < count <= 1000 * 0.15 // 50


def test_recruit_waits_while_the_barracks_queue_is_long():
    ctx = context(units=[unit("spear", 10)])
    ctx.village.recruit_orders = [RecruitOrderOut(unit="spear", count=20, finishes_at=datetime.now(UTC) + timedelta(hours=2))]

    assert Routines.queue_minutes(ctx) > 60


def test_spears_come_first_until_the_scavenging_army_is_there():
    ctx = context(units=[unit("spear", 5), unit("axe", 0)])

    assert Routines.recruit_unit(ctx) == "spear"
