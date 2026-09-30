import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import context, unit
from tribal_assistant.core.agents.guardrails import Guardrails
from tribal_assistant.core.agents.knobs import KnobStore
from tribal_assistant.core.agents.learning import LessonBook
from tribal_assistant.core.agents.proposers.attack import AttackProposer
from tribal_assistant.core.agents.proposers.raid import RaidPlanner
from tribal_assistant.core.agents.proposers.recruitment import RecruitmentProposer
from tribal_assistant.core.agents.squads import MIN_POP, UNIT_POP, MinimumSquad
from tribal_assistant.core.agents.target_intel import TargetIntel
from tribal_assistant.core.game.modules.game_sync import REPORT_DETAIL_JS
from tribal_assistant.core.game.scraper.game import ReportSnapshot
from tribal_assistant.core.game.scraper.spy_report import SpyReportParser
from tribal_assistant.core.models.world import WorldVillage
from tribal_assistant.core.schemas.agent_settings import AgentSettings

FIXTURE = Path(__file__).parents[1] / "fixtures" / "html" / "report_spy.html"


def captured_sections() -> str:
    selector = re.search(r"sections: html\('([^']+)'\)", REPORT_DETAIL_JS).group(1)
    soup = BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "lxml")
    return "".join(str(node) for node in soup.select(selector))


def ago(hours: float) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


def test_spy_report_sections_become_numbers():
    intel = SpyReportParser.parse(captured_sections())

    assert intel["scouted"] == {"wood": 1234, "clay": 987, "iron": 2005}
    assert intel["wall"] == 2
    assert intel["buildings"]["storage"] == 7 and intel["buildings"]["hide"] == 2
    assert intel["attacker_units"] == {"spy": 1} and intel["attacker_losses"] == {}
    assert intel["defender_units"] == {"spear": 12}


def test_spy_buildings_fall_back_to_the_tables():
    html = re.sub(r'<input type="hidden" id="attack_spy_building_data"[^>]*>', "", FIXTURE.read_text(encoding="utf-8"))

    assert SpyReportParser.parse(html)["buildings"] == {"main": 3, "wall": 2}
    assert SpyReportParser.parse("") == {}
    assert "scouted" not in SpyReportParser.parse("<table id='attack_info_def_units'></table>")


def test_wall_table_and_rams():
    assert [RaidPlanner.wall_light(w, has_ram=True) for w in range(6)] == [1, 2, 8, 22, 46, 85]
    assert RaidPlanner.wall_light(3) is None
    assert RaidPlanner.wall_light(2) == 8
    assert RaidPlanner.wall_light(None) == 0
    assert RaidPlanner.wall_light(9, has_ram=True) is None


def test_haul_is_sized_by_scouted_stock_plus_production_until_arrival():
    scouted = {"wood": 1000, "clay": 1000, "iron": 1000}

    assert RaidPlanner.haul_estimate(scouted, {"wood": 1, "stone": 1, "iron": 1, "storage": 10}, 1.0) == 3180
    assert RaidPlanner.haul_estimate(scouted, {"storage": 1}, 10.0) == 3000
    assert RaidPlanner.haul_estimate(scouted, {"storage": 10, "hide": 1}, 0.0) == 2550

    data = {"scouted": scouted, "scouted_at": ago(0), "buildings": {"wood": 1, "stone": 1, "iron": 1, "storage": 10}}
    plan = RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 50}, {**data, "attacks": 1, "wall": 0}, {"light": 100}, 50)
    assert plan.kind == "raid" and plan.squad["light"] == 40

    stale = {**data, "looted_at": ago(0), "scouted_at": ago(1), "avg_haul": 200, "attacks": 1}
    assert RaidPlanner.expected(stale, 1.0) is None


def test_radius_follows_unit_speed():
    assert RaidPlanner.minutes_per_field("spear") == 36
    assert RaidPlanner.minutes_per_field("light") == 20
    assert RaidPlanner.in_range("spear", 4) and not RaidPlanner.in_range("spear", 5)
    assert RaidPlanner.in_range("light", 10) and not RaidPlanner.in_range("light", 10.5)

    known = {"attacks": 2, "last_result": "green", "avg_haul": 300}
    far = RaidPlanner.plan({"coords": "507|500", "distance": 7, "points": 40}, known, {"spear": 100}, 50)
    assert far.kind == "skip"

    near = RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 40}, known, {"spear": 100}, 50)
    assert near.kind == "raid" and near.squad == {"spear": 14}


def test_targets_are_probed_first_then_ranked_by_haul_per_hour():
    home = {"light": 50, "spy": 6}
    known = {"attacks": 3, "last_result": "green", "avg_haul": 400}

    unknown = RaidPlanner.plan({"coords": "501|500", "distance": 1, "points": 30}, {}, home, 60)
    assert unknown.kind == "probe" and unknown.squad == {"spy": 5}

    yellow = RaidPlanner.plan({"coords": "502|500", "distance": 2, "points": 30}, {**known, "yellow_streak": 1}, home, 60)
    assert yellow.kind == "probe"

    big = RaidPlanner.plan({"coords": "502|501", "distance": 2, "points": 900}, known, {"light": 50}, 60)
    assert big.kind == "skip"

    close = RaidPlanner.plan({"coords": "502|500", "distance": 2, "points": 30}, known, home, 60)
    rich = RaidPlanner.plan({"coords": "506|500", "distance": 6, "points": 30}, {**known, "avg_haul": 2000}, home, 60)
    poor = RaidPlanner.plan({"coords": "506|501", "distance": 6, "points": 30}, {**known, "avg_haul": 100}, home, 60)
    assert close.kind == rich.kind == poor.kind == "raid"
    assert rich.rate > close.rate > poor.rate

    walled = RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 30}, {**known, "wall": 3}, home, 60)
    assert walled.kind == "skip"

    guarded = RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 30}, {**known, "defenders_left": 4}, home, 60)
    assert guarded.kind == "skip"


def test_wall_needs_the_light_cavalry_of_the_table():
    known = {"attacks": 1, "last_result": "green", "avg_haul": 100, "wall": 2}

    plan = RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 30}, known, {"light": 20, "spear": 100}, 60)
    assert plan.squad == {"light": 8}

    assert RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 30}, known, {"light": 5, "spear": 100}, 60).kind == "skip"

    open_village = RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 30}, {**known, "wall": 0}, {"light": 20, "spy": 2}, 60)
    assert open_village.squad == {"light": 2, "spy": 1}


def test_paladin_only_on_green_or_small_targets_and_infantry_never_alone():
    assert RaidPlanner.paladin_allowed({"last_result": "green"}, 500)
    assert RaidPlanner.paladin_allowed({}, 90)
    assert not RaidPlanner.paladin_allowed({"last_result": "yellow"}, 300)

    home = {"knight": 1, "spear": 30}
    yellow = {"attacks": 2, "last_result": "yellow", "avg_haul": 200, "scouted": {"wood": 0}, "scouted_at": ago(0), "looted_at": ago(1)}
    plan = RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 300}, yellow, home, 500)
    assert "knight" not in plan.squad

    green = {"attacks": 2, "last_result": "green", "avg_haul": 200}
    assert RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 300}, green, home, 500).squad == {"knight": 1, "spear": 6}

    few = RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 300}, {**green, "avg_haul": 50}, {"spear": 30}, 500)
    assert few.squad == {"spear": 10}
    assert RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": 300}, {**green, "avg_haul": 50}, {"spear": 6}, 500).kind == "skip"


def test_raid_count_grows_with_light_cavalry_inside_the_hourly_limit():
    assert RaidPlanner.max_raids(0, 12, 0) == 3
    assert RaidPlanner.max_raids(100, 12, 0) == 8
    assert RaidPlanner.max_raids(1000, 30, 0) == 12
    assert RaidPlanner.max_raids(100, 12, 10) == 2
    assert RaidPlanner.max_raids(100, 0, 0) == 0


def test_scavenging_300_spears_on_four_free_tiers_uses_medium_large_extreme():
    parts = AttackProposer.split({"spear": 300}, {1: 0.10, 2: 0.25, 3: 0.50, 4: 0.75})

    assert set(parts) == {2, 3, 4}
    assert [parts[t]["spear"] for t in (2, 3, 4)] == [163, 81, 56]
    assert sum(p["spear"] for p in parts.values()) == 300


def test_spies_follow_light_cavalry():
    assert RecruitmentProposer.spy_target(0) == 5
    assert RecruitmentProposer.spy_target(100) == 20


async def test_reports_store_scouting_on_the_target(session: AsyncSession):
    book = LessonBook(session)
    raid = ReportSnapshot("1", "ataca", "attack", "yellow", False, None, "500|500", "503|501", 30, 20, 10, 60)
    probe = ReportSnapshot("2", "ataca", "attack", "blue", False, None, "500|500", "503|501")
    intel = SpyReportParser.parse(captured_sections())
    intel["defender_units"] = {"spear": 12}
    intel["defender_losses"] = {"spear": 12}

    await book.reports([raid], set(), {"1": {"attacker_units": {"light": 5}, "attacker_losses": {"light": 1}}})
    await book.reports([probe], {"1"}, {"2": intel})

    target = await book.target("503|501")
    assert target["attacks"] == 1 and target["avg_haul"] == 60 and target["losses"] == {"light": 1}
    assert target["wall"] == 2 and target["scouted"]["iron"] == 2005 and target["yellow_streak"] == 0
    assert TargetIntel.fresh_scouting(target)

    summary = TargetIntel.summary("503|501", target)
    assert summary["wall"] == 2 and summary["scouted_hours_ago"] == 0.0 and summary["defenders_left"] == 0


async def test_spy_probe_guardrails(session: AsyncSession):
    session.add_all(
        [
            WorldVillage(id=1, name="Bárbara", x=503, y=500, player_id=0, points=30),
            WorldVillage(id=2, name="Jogador", x=502, y=500, player_id=77, points=300),
        ]
    )
    await session.commit()

    guard = Guardrails(session, AgentSettings())
    ctx = context(units=[unit("spear", 10), unit("spy", 3)])

    assert await guard.check_spy(ctx, "503|500", 1) is None
    assert "de 1 a 2" in await guard.check_spy(ctx, "503|500", 3)
    assert "bárbara" in await guard.check_spy(ctx, "502|500", 1)
    assert "só há" in await guard.check_spy(context(units=[unit("spear", 10)]), "503|500", 1)
    assert await guard.attacks_last_hour(ctx) == 0


@pytest.mark.parametrize("points", [30, 90])
def test_small_unknown_targets_are_raided_when_there_are_no_spies(points: int):
    plan = RaidPlanner.plan({"coords": "503|500", "distance": 3, "points": points}, {}, {"light": 10}, 100)
    assert plan.kind == "raid"


async def test_the_game_refusal_raises_the_minimum_spies(session):
    found = MIN_POP.search("Cada ataque desta aldeia precisa de pelo menos 14 de população. Você está tentando enviar 10.")
    assert await MinimumSquad(session).learn("spy.min_send", int(found.group(1)), UNIT_POP["spy"]) == 7
    assert (await KnobStore(session).load()).int("spy.min_send") == 7
    assert await MinimumSquad(session).learn("spy.min_send", 4, UNIT_POP["spy"]) == 7
