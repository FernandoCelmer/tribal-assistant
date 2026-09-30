from tribal_assistant.core.game.narrator import MAX_ARGS, Narrator


def test_arguments_drop_reason_and_empty_values():
    text = Narrator.arguments({"building": "farm", "reason": "porque sim", "note": "", "units": {"spear": 5}})

    assert text == 'building=farm, units={"spear": 5}'


def test_arguments_are_shortened():
    assert len(Narrator.arguments({"text": "x" * 1_000})) == MAX_ARGS
