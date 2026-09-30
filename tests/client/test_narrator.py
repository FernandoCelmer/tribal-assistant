from tribal_assistant.core.game.narrator import MAX_ARGS, Narrator


def test_arguments_drop_reason_and_empty_values():
    text = Narrator.arguments({"building": "farm", "reason": "porque sim", "note": "", "units": {"spear": 5}})

    assert text == 'building=farm, units={"spear": 5}'


def test_arguments_are_shortened():
    assert len(Narrator.arguments({"text": "x" * 1_000})) == MAX_ARGS


def test_query_reads_game_urls_only():
    assert Narrator.query("https://br144.tribalwars.com.br/game.php?village=1&screen=am_farm&mode=farm") == {"village": "1", "screen": "am_farm", "mode": "farm"}
    assert Narrator.query("https://www.tribalwars.com.br/page/login") is None


def test_place_names_screens_and_modes():
    assert Narrator.place("am_farm", {}) == "assistente de saque"
    assert Narrator.place("market", {"mode": "own_offer"}) == "mercado (own offer)"
