from tribal_assistant.core.game.forge import Forge


def test_forge_tries_a_new_formula_before_a_known_one() -> None:
    assert Forge.pick({"1": 3, "2": 1, "3": 0}, {"1-1-1": "42673"}) == ["1", "1", "2"]


def test_forge_falls_back_to_a_known_formula() -> None:
    assert Forge.pick({"1": 3, "2": 0}, {"1-1-1": "42673"}) == ["1", "1", "1"]


def test_forge_waits_for_three_materials() -> None:
    assert Forge.pick({"1": 2, "2": 0}, {}) is None


def test_diplomacy_picks_the_strongest_tribe_and_the_recommended_mentor() -> None:
    from tribal_assistant.core.game.diplomacy import Diplomacy

    nearby = [{"id": "239", "tag": "LARGA3", "members": 31, "points": 44304}, {"id": "1289", "tag": "UKR", "members": 1, "points": 183}, {"id": "1165", "tag": "MINA3", "members": 59, "points": 144071}]
    assert Diplomacy.best_tribe(nearby, set())["tag"] == "MINA3"
    assert Diplomacy.best_tribe(nearby, {"1165"})["tag"] == "LARGA3"
    assert Diplomacy.best_tribe(nearby, {"1165", "239"}) is None

    mentors = [{"id": "1", "name": "Noia Armado", "rank": 234, "recommended": True}, {"id": "2", "name": "Chonguera", "rank": 81, "recommended": False}]
    assert Diplomacy.best_mentor(mentors, set())["name"] == "Noia Armado"
    assert Diplomacy.best_mentor(mentors, {"Noia Armado"})["name"] == "Chonguera"
