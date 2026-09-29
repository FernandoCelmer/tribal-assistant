import pytest

from tribal_assistant.core.accounts.context import AccountContext
from tribal_assistant.core.config import settings
from tribal_assistant.core.errors import ConflictError
from tribal_assistant.core.game.session import GameSession


async def test_a_panel_only_server_never_opens_the_game_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "play", False)
    session = GameSession(AccountContext(id=1, name="t", server="br1", world_url="https://br1.example", username="u", password="p"))

    with pytest.raises(ConflictError):
        await session.page()
