from tribal_assistant.core.game.forge import Forge


def test_forge_tries_a_new_formula_before_a_known_one() -> None:
    assert Forge.pick({"1": 3, "2": 1, "3": 0}, {"1-1-1": "42673"}) == ["1", "1", "2"]


def test_forge_falls_back_to_a_known_formula() -> None:
    assert Forge.pick({"1": 3, "2": 0}, {"1-1-1": "42673"}) == ["1", "1", "1"]


def test_forge_waits_for_three_materials() -> None:
    assert Forge.pick({"1": 2, "2": 0}, {}) is None
