from datetime import UTC, datetime, timedelta

import pytest

from tribal_assistant.core.game.actions import ActionResult
from tribal_assistant.core.game.modules import free_finish
from tribal_assistant.core.game.modules.free_finish import FreeFinishWatcher
from tribal_assistant.core.models.building import Building
from tribal_assistant.core.models.village import Village


class FakeActions:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def finish_free(self, village_id: str) -> ActionResult:
        self.calls.append(village_id)
        return ActionResult(True, "finish_free", "ok", {"finished": 1})


@pytest.mark.asyncio
async def test_opens_only_villages_with_orders_inside_the_window(session, monkeypatch):
    monkeypatch.setattr(free_finish, "SessionFactory", lambda: _Ctx(session))
    now = datetime.now(UTC).replace(tzinfo=None)

    soon = Village(game_id="1", name="A", coords="1|1", is_own=True)
    later = Village(game_id="2", name="B", coords="2|2", is_own=True)
    session.add_all([soon, later])
    await session.flush()
    session.add_all([
        Building(village_id=soon.id, name="main", level=3, queued_until=now + timedelta(minutes=2)),
        Building(village_id=later.id, name="main", level=3, queued_until=now + timedelta(hours=1)),
    ])
    await session.commit()

    actions = FakeActions()
    finished = await FreeFinishWatcher(actions).run()

    assert actions.calls == ["1"]
    assert finished == 1


class _Ctx:
    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc) -> None:
        return None
