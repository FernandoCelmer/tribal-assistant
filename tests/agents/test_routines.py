from datetime import UTC, datetime, timedelta

from tests.agents.builders import context, unit
from tribal_assistant.core.agents.routines import Routines
from tribal_assistant.core.schemas.game import RecruitOrderOut


def test_troops_home_count_their_population_without_the_paladin():
    ctx = context(units=[unit("spear", 20), unit("sword", 5), unit("knight", 1)])

    assert Routines.troops_home(ctx) == 25


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
