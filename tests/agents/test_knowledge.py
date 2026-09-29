from tribal_assistant.core.agents.knowledge import GameKnowledge


def test_quest_goal_maps_to_building_and_level() -> None:
    assert GameKnowledge.goal_building("Expanda Poço de argila ao nível 5.") == ("stone", 5)
    assert GameKnowledge.goal_building("Melhore Quartel Expanda Quartel ao nível 3.") == ("barracks", 3)
    assert GameKnowledge.goal_building("Junte-se a uma tribo") is None


def test_missing_requirements_from_docs() -> None:
    assert GameKnowledge.missing_requirements("stable", {"barracks": 5, "smith": 5, "main": 10}) == {}
    assert GameKnowledge.missing_requirements("snob", {"main": 20}) == {"market": 10, "smith": 20}


def test_unit_and_building_lookups() -> None:
    assert GameKnowledge.unit("light")["carry"] == 80
    assert GameKnowledge.building("Academia")["id"] == "snob"
    assert GameKnowledge.building("nope") is None


def test_guides_are_packaged_and_readable():
    from tribal_assistant.core.agents.knowledge import GameKnowledge

    for name in GameKnowledge.guides:
        assert len(GameKnowledge.guide(name) or "") > 1000

    assert GameKnowledge.guide("nada") is None
