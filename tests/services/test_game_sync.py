from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.client.scraper.game import (
    GameSnapshot,
    parse_commands,
    parse_player,
    parse_protection,
    parse_queue,
    parse_report_date,
    parse_reports,
    parse_scavenge,
    parse_village,
)
from tribal_assistant.repositories.game import GameRepository

GAME_DATA = {
    "world": "br144",
    "player": {"id": 920113687, "name": "Frenor", "points": "77", "rank": 46954,
               "villages": "1", "incomings": "0", "pp": "30", "new_report": "2",
               "new_igm": "0", "new_quest": "1", "new_daily_bonus": "0", "ally": "0"},
    "village": {
        "id": 105765, "name": "Frenor de aldeia", "coord": "482|754", "x": 482, "y": 754,
        "points": 77, "wood": 806, "stone": 906, "iron": 695, "storage_max": 1229,
        "pop": 70, "pop_max": 281, "wood_prod": 0.026225279658755,
        "stone_prod": 0.026225279658755, "iron_prod": 0.016666666666667,
        "buildings": {"main": "3", "wood": "4", "stone": "4", "iron": "1", "farm": "2",
                      "storage": "2", "stable": "0"},
    },
}
UPGRADES = {
    "main": {"level_next": 4, "max_level": 30, "wood": 180, "stone": 166, "iron": 140,
             "pop": 1, "build_time": 194, "can_build": True, "error": None},
    "iron": {"level_next": 2, "max_level": 30, "wood": 94, "stone": 94, "iron": 72,
             "pop": 1, "build_time": 100, "can_build": True, "error": None},
    "storage": {"level_next": 3, "max_level": 30, "wood": 76, "stone": 64, "iron": 50,
                "pop": 0, "build_time": 90, "can_build": False, "error": "Fila cheia"},
}
BUILD_QUEUE = [{"building": "farm", "text": "Fazenda\nNível 3", "end": "1790640000"}]
TRAIN = [
    {"name": "spear", "available": True, "home": "10", "total": "10", "max": "16",
     "wood": "50", "stone": "30", "iron": "10", "pop": "1", "time": "0:05:03"},
    {"name": "sword", "available": False, "requirements": "Ferreiro (Nível 1)"},
]
HOME = [{"name": "spear", "count": "10"}, {"name": "sword", "count": "10"}]
RECRUIT = [{"unit": "spear", "text": "5 Lanceiros", "end": "1790641000"}]
COMMANDS = [
    {"direction": "in", "id": "9", "icon": "graphic/command/attack.png", "text": "Ataque", "end": "1790642000"},
    {"direction": "out", "id": "10", "icon": "graphic/command/return.png",
     "text": "Retorno de Bárbaros (480|750) K74", "end": "1790643000"},
]
SCAVENGE = [
    {"id": 1, "name": "Pequena Coleta", "loot_factor": 0.1, "locked": False, "unlock_time": None,
     "squad": {"return_time": 1790644000, "unit_counts": {"spear": 10}}},
    {"id": 2, "name": "Média Coleta", "loot_factor": 0.25, "locked": True, "unlock_time": None, "squad": None},
]
NOW = datetime(2026, 9, 28, 23, 0, tzinfo=UTC)


def _village():
    return parse_village(GAME_DATA, UPGRADES, BUILD_QUEUE, TRAIN, home_rows=HOME,
                         recruit_rows=RECRUIT, command_rows=COMMANDS, scavenge_rows=SCAVENGE)


def test_parse_player_flags() -> None:
    player = parse_player(GAME_DATA, "A sua proteção de iniciante acaba em 03.10. às 20:38:21")
    assert (player.name, player.points, player.premium_points, player.new_reports) == ("Frenor", 77, 30, 2)
    assert player.new_quests and not player.daily_bonus and player.ally_id is None
    assert player.protection_until is not None and player.protection_until.day == 3


def test_parse_village_everything() -> None:
    village = _village()
    assert village.coords == "482|754"
    assert village.wood_prod == 94

    buildings = {b.name: b for b in village.buildings}
    assert buildings["main"].next_level == 4 and buildings["main"].next_wood == 180
    assert buildings["storage"].blocker == "Fila cheia"
    assert buildings["stable"].blocker == "requisitos não atendidos"
    assert buildings["farm"].queued_level == 3

    units = {u.name: u for u in village.units}
    assert units["spear"].available and units["spear"].max_recruit == 16
    assert units["spear"].build_time == 303
    assert not units["sword"].available and units["sword"].home == 10
    assert units["sword"].blocker == "Ferreiro (Nível 1)"

    assert village.recruit_queue[0].count == 5
    assert [c.kind for c in village.commands] == ["attack", "return"]
    assert village.commands[1].coords == "480|750"
    assert village.scavenge[0].return_at == datetime.fromtimestamp(1790644000, UTC)
    assert village.scavenge[1].is_locked


def test_parse_queue_keeps_highest_level() -> None:
    rows = [{"building": "wood", "text": "Bosque Nível 5", "end": "10"},
            {"building": "wood", "text": "Bosque Nível 6", "end": "20"}]
    assert parse_queue(rows)["wood"][0] == 6


def test_parse_dates_in_server_time() -> None:
    assert parse_protection("acaba em 03.10. às 20:38:21", NOW) == datetime(2026, 10, 3, 23, 38, 21, tzinfo=UTC)
    assert parse_report_date("set. 28, 20:42", NOW) == datetime(2026, 9, 28, 23, 42, tzinfo=UTC)
    assert parse_report_date("hoje às 10:00", NOW) == datetime(2026, 9, 28, 13, 0, tzinfo=UTC)


def test_parse_reports_with_attack_detail() -> None:
    rows = [{"id": "5", "title": "Frenor (Aldeia) ataca Bárbaros (480|750)", "received": "set. 28, 20:42",
             "icons": "graphic/dots/green.png", "is_new": True}]
    details = {"5": {"attacker": "Frenor de aldeia (482|754)", "defender": "Aldeia (480|750)",
                     "loot": ["120", "80", "40"], "haul": "240/250"}}
    (report,) = parse_reports(rows, details, NOW)
    assert (report.category, report.result, report.loot_wood, report.haul_total) == ("attack", "green", 120, 250)
    assert (report.origin_coords, report.target_coords) == ("482|754", "480|750")


def test_parse_commands_skips_rows_without_time() -> None:
    assert parse_commands([{"direction": "in", "text": "x"}]) == ()


def test_parse_scavenge_handles_missing_squad() -> None:
    (option,) = parse_scavenge([{"id": 3, "name": "Grande", "locked": True}])
    assert option.return_at is None and option.squad_json is None


async def test_persist_is_idempotent(session: AsyncSession) -> None:
    snapshot = GameSnapshot(
        player=parse_player(GAME_DATA),
        villages=(_village(),),
        reports=parse_reports([{"id": "1", "title": "Realização alcançada", "received": "set. 28, 20:42"}]),
    )
    repository = GameRepository(session)
    await repository.persist(snapshot)
    await repository.persist(snapshot)

    (village,) = await repository.own_villages()
    assert village.game_id == "105765"
    assert len(village.buildings) == 7
    assert {u.name: u.home for u in village.units} == {"spear": 10, "sword": 10}
    assert len(village.commands) == 2 and len(village.recruit_orders) == 1
    assert len(village.scavenge_options) == 2
    assert await repository.report_ids() == {"1"}
