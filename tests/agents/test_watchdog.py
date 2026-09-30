from tribal_assistant.core.agents.watchdog import Watchdog

STUCK = {
    "budget": {"stock": {"wood": 914, "clay": 859, "iron": 927}, "free": {"wood": 0, "clay": 0, "iron": 0}},
    "insights": [{"text": "fila de obras: 0 ordem(ns), termina em 0.0h"}],
    "deferred": [
        {"why": "consumiria recursos reservados para research:axe, plan:wall"},
        {"why": "consumiria recursos reservados para research:axe"},
    ],
}
MOVING = {"budget": {"stock": {"wood": 900}, "free": {"wood": 300, "clay": 200, "iron": 100}}, "insights": [], "deferred": []}


def test_the_reservation_that_keeps_the_village_stuck_is_found():
    assert Watchdog.blocker([STUCK] * 5, 5) == "research:axe"


def test_a_village_that_still_moves_is_left_alone():
    assert Watchdog.blocker([STUCK] * 3 + [MOVING] * 5, 5) is None
