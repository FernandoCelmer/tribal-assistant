from pathlib import Path

from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import context, scavenge, unit
from tribal_assistant.core.agents.guardrails import Guardrails
from tribal_assistant.core.schemas.agent_settings import AgentSettings


def _guard(session: AsyncSession) -> Guardrails:
    return Guardrails(session, AgentSettings())


def test_unlock_goes_in_order_one_at_a_time(session: AsyncSession) -> None:
    guard = _guard(session)
    options = [scavenge(1, locked=True), scavenge(2, locked=True)]

    assert guard.check_unlock_scavenge(context(scavenge_options=options), 1) is None
    assert "primeiro" in guard.check_unlock_scavenge(context(scavenge_options=options), 2)

    busy = [scavenge(1, locked=True, unlocking=True), scavenge(2, locked=True)]
    assert "já está sendo" in guard.check_unlock_scavenge(context(scavenge_options=busy), 1)

    done = [scavenge(1), scavenge(2, locked=True)]
    assert "já está desbloqueada" in guard.check_unlock_scavenge(context(scavenge_options=done), 1)


def test_scavenge_needs_free_unlocked_tier_and_troops(session: AsyncSession) -> None:
    guard = _guard(session)
    ctx = context(units=[unit("spear", 10)], scavenge_options=[scavenge(1), scavenge(2, busy=True), scavenge(3, locked=True)])

    assert guard.check_scavenge(ctx, 1, {"spear": 10}) is None
    assert "em andamento" in guard.check_scavenge(ctx, 2, {"spear": 1})
    assert "bloqueada" in guard.check_scavenge(ctx, 3, {"spear": 1})
    assert "só há" in guard.check_scavenge(ctx, 1, {"spear": 11})


def test_free_finish_selector_never_matches_premium_buttons() -> None:
    html = """<table id="buildqueue"><tr>
      <td><a class="btn btn-btr order_feature" href="#">Reduzir</a></td>
      <td><a class="btn btn-instant-free" href="#">Concluir</a></td></tr></table>"""
    soup = BeautifulSoup(html, "lxml")

    matches = soup.select("#buildqueue .btn-instant-free")
    assert [m.get_text() for m in matches] == ["Concluir"]


def test_scavenge_markup_has_free_and_premium_buttons_apart() -> None:
    path = Path(__file__).parents[1] / "fixtures" / "html" / "scavenge.html"
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")

    assert soup.select_one(".options-container .scavenge-option .free_send_button") is not None
    assert soup.select_one("input.unitsInput[name='spear']") is not None
    assert "free_send_button" not in (soup.select_one(".premium_send_button").get("class") or [])
