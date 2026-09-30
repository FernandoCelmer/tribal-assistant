from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.accounts.context import AccountContext, use_account
from tribal_assistant.core.crypto import Vault
from tribal_assistant.core.models.lesson import Lesson
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.models.world import WorldVillage

A = AccountContext(id=1, name="a", server="br144", world_url="https://br144.x", username="a", password="p")
B = AccountContext(id=2, name="b", server="br145", world_url="https://br145.x", username="b", password="p")


async def test_each_account_only_sees_its_own_rows(session: AsyncSession) -> None:
    with use_account(A):
        session.add(Village(game_id="1", name="da conta A", coords="1|1", is_own=True))
        await session.commit()

    with use_account(B):
        session.add(Village(game_id="1", name="da conta B", coords="2|2", is_own=True))
        await session.commit()
        names = (await session.execute(select(Village.name))).scalars().all()
        assert names == ["da conta B"]

    with use_account(A):
        names = (await session.execute(select(Village.name))).scalars().all()
        assert names == ["da conta A"]

    everything = (await session.execute(select(Village.name).execution_options(all_accounts=True))).scalars().all()
    assert sorted(everything) == ["da conta A", "da conta B"]


async def test_world_data_is_shared_by_world_not_by_account(session: AsyncSession) -> None:
    with use_account(A):
        session.add(WorldVillage(id=9, name="bárbara 144", x=1, y=1, player_id=0, points=30))
        await session.commit()

    with use_account(B):
        session.add(WorldVillage(id=9, name="bárbara 145", x=1, y=1, player_id=0, points=30))
        await session.commit()
        assert (await session.execute(select(WorldVillage.name))).scalars().all() == ["bárbara 145"]


async def test_same_lesson_key_can_exist_per_account(session: AsyncSession) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    for account in (A, B):
        with use_account(account):
            session.add(Lesson(key="rule:x", topic="rule", title="t", first_seen=now, last_seen=now))
            await session.commit()

    with use_account(B):
        assert len((await session.execute(select(Lesson))).scalars().all()) == 1


def test_passwords_are_encrypted(tmp_path) -> None:
    vault = Vault(key_file=str(tmp_path / "k"))
    token = vault.encrypt("segredo")

    assert token != "segredo"
    assert vault.decrypt(token) == "segredo"
