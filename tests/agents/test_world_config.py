from tribal_assistant.core.game.world_config import WorldConfig

CONFIG = {
    "speed": 2,
    "unit_speed": 0.5,
    "game": {"knight": 1, "archer": 1, "church": 0, "watchtower": 1, "barbarian_rise": 0.003, "barbarian_max_points": 2000},
    "snob": {"gold": 1, "coin_wood": 28000, "coin_stone": 30000, "coin_iron": 25000, "rise": 1, "max_dist": 50},
    "night": {"active": 1, "start_hour": 0, "end_hour": 8, "def_factor": 2},
    "newbie": {"days": 5},
}
UNITS = {"spear": {"speed": 36}, "militia": {"speed": 0.02}}


def test_reads_world_rules_from_config() -> None:
    world = WorldConfig.from_settings(CONFIG, UNITS)

    assert (world.speed, world.unit_speed) == (2, 0.5)
    assert world.noble_system == "coins"
    assert world.knight and world.archer and world.watchtower and not world.church
    assert world.militia
    assert world.barbarian_rise == 0.003 and world.barbarian_max_points == 2000
    assert world.night.active and (world.night.start_hour, world.night.end_hour, world.night.defense_factor) == (0, 8, 2)
    assert world.protection_days == 5
    assert world.noble_max_distance == 50
    assert world.loyalty_per_hour == 2
    assert "moedas" in world.summary()


def test_missing_config_falls_back_to_defaults() -> None:
    world = WorldConfig.from_settings({}, None)

    assert world.speed == 1 and world.noble_system == "coins" and not world.militia
    assert world.noble_cost(1) == {"wood": 68000, "clay": 80000, "iron": 75000}


def test_noble_cost_by_system() -> None:
    coins = WorldConfig.from_settings(CONFIG)
    packages = WorldConfig.from_settings({**CONFIG, "snob": {**CONFIG["snob"], "gold": 0}})
    levels = WorldConfig.from_settings({**CONFIG, "snob": {"gold": 2}})

    assert coins.noble_cost(1) == {"wood": 68000, "clay": 80000, "iron": 75000}
    assert coins.noble_cost(3) == {"wood": 124000, "clay": 140000, "iron": 125000}
    assert packages.noble_system == "packages"
    assert packages.noble_cost(2) == {"wood": 96000, "clay": 110000, "iron": 100000}
    assert levels.noble_system == "levels"
    assert levels.noble_cost(4) == {"wood": 40000, "clay": 50000, "iron": 50000}
