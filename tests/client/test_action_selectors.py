from pathlib import Path

import pytest
from bs4 import BeautifulSoup

FIXTURES = Path(__file__).parents[1] / "fixtures" / "html"


def _soup(name: str) -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / name).read_text(encoding="utf-8"), "lxml")


@pytest.mark.parametrize(
    ("fixture", "selector"),
    [
        ("main.html", 'a.btn-build:not(.btn-bcr)[data-building="wood"]'),
        ("main.html", 'a.btn-build:not(.btn-bcr)[data-building="barracks"]'),
        ("barracks.html", "#train_form input[name='spear']"),
        ("barracks.html", "#train_form .btn-recruit"),
        ("place.html", "#unit_input_spear"),
        ("place.html", "#target_attack"),
        ("place.html", "input.target-input-field"),
        ("place_confirm.html", "#troop_confirm_submit"),
        ("quests.html", ".quest-popup-container a.quest-link[data-quest-id='1210']"),
        ("quests.html", "#reward-tab .reward-system-claim-button"),
    ],
)
def test_action_selectors_match_real_markup(fixture: str, selector: str) -> None:
    assert _soup(fixture).select_one(selector) is not None


def test_upgrade_button_carries_next_level() -> None:
    button = _soup("main.html").select_one('a.btn-build:not(.btn-bcr)[data-building="main"]')

    assert button is not None
    assert button["data-level-next"] == "4"


def test_fixtures_have_no_csrf_tokens() -> None:
    for path in FIXTURES.glob("*.html"):
        assert "b4a3bbfa" not in path.read_text(encoding="utf-8")
