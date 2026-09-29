import pytest

from tribal_assistant.core.game.battle import simulate_battle
from tribal_assistant.core.game.incoming import (
    IncomingLabel,
    TravelClock,
    distance,
    guess_army,
    size_of,
    tag_for,
)


def test_no_defense_is_a_win_without_losses() -> None:
    result = simulate_battle({"axe": 100}, {})

    assert result.attacker_wins
    assert result.attacker_losses == {"axe": 0}
    assert result.defense == 20


def test_winner_loses_by_the_power_of_one_and_a_half() -> None:
    result = simulate_battle({"axe": 100}, {"spear": 50, "sword": 50})

    assert result.attack == 4000
    assert result.defense == 3270
    assert result.attacker_loss_ratio == pytest.approx((3270 / 4000) ** 1.5)
    assert result.defender_losses == {"spear": 50, "sword": 50}


def test_high_wall_turns_the_battle_and_raises_losses() -> None:
    low = simulate_battle({"axe": 100}, {"spear": 50, "sword": 50}, wall=0)
    high = simulate_battle({"axe": 100}, {"spear": 50, "sword": 50}, wall=10)

    assert low.attacker_wins and not high.attacker_wins
    assert high.defense == pytest.approx(3250 * 1.037**10 + 20 + 500)
    assert high.attacker_losses["axe"] == 100
    assert simulate_battle({"axe": 300}, {"spear": 50}, wall=5).attacker_loss_ratio > simulate_battle({"axe": 300}, {"spear": 50}).attacker_loss_ratio


def test_attack_is_split_by_type_against_matching_defense() -> None:
    cavalry = simulate_battle({"light": 100}, {"spear": 100})
    infantry = simulate_battle({"axe": 325}, {"spear": 100})

    assert cavalry.defense == 100 * 45 + 20
    assert infantry.defense == 100 * 15 + 20
    mixed = simulate_battle({"axe": 100, "light": 100}, {"spear": 100})
    assert mixed.defense == pytest.approx(100 * (15 * 4000 / 17000 + 45 * 13000 / 17000) + 20)


def test_spies_do_not_fight() -> None:
    result = simulate_battle({"spy": 5}, {"spear": 1})

    assert not result.attacker_wins and result.attacker_losses == {}


def test_travel_clock_uses_world_speeds_and_noble_is_seven_sixths_of_a_ram() -> None:
    base = TravelClock.for_world(None, {"speed": 2, "unit_speed": 0.5})
    assert base.minutes("ram", 10) == 300
    assert base.minutes("snob", 6) == pytest.approx(210)

    fast = TravelClock.for_world({"ram": {"speed": 15}, "light": {"speed": 5}})
    assert fast.table["snob"] == pytest.approx(17.5)
    assert fast.minutes("light", 2) == 10


def test_slowest_unit_follows_the_time_left_when_first_seen() -> None:
    clock = TravelClock()

    assert clock.slowest(10, 95) == "light"
    assert clock.slowest(10, 105) == "heavy"
    assert clock.slowest(10, 250) == "ram"
    assert clock.slowest(10, 320) == "snob"
    assert clock.slowest(10, 400) is None
    assert clock.slowest(None, 50) is None


def test_label_keeps_origin_player_size_and_watchtower() -> None:
    label = IncomingLabel.compose("Ataque", "medium", "Vizinho Mau", "480|750", True)
    parsed = IncomingLabel.parse(label)

    assert parsed == {"name": "Ataque", "size": "medium", "player": "Vizinho Mau", "origin": "480|750", "watchtower": True}
    assert IncomingLabel.parse("Ataque")["origin"] is None
    assert size_of("graphic/command/attack_small.webp") == "small"
    assert size_of("", "Ataque grande (5000+ tropas)") == "large"
    assert distance("500|500", "503|504") == 5


def test_tags_and_army_guess() -> None:
    assert tag_for("light") == "CL"
    assert tag_for("ram", "small") == "fake"
    assert tag_for("axe", noble=True) == "nobre"
    assert tag_for(None) == "desconhecido"

    assert guess_army("axe", "small", 300).units == {"axe": 195, "light": 26}
    assert guess_army("light", None, 400).units == {"light": 100}
    assert guess_army("spy", "small", 300).units == {"spy": 5}
    assert guess_army(None, None, None) is None
