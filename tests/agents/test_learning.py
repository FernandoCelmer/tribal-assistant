import pytest

from tribal_assistant.agents.learning import LessonBook
from tribal_assistant.repositories.lessons import LessonRepository


@pytest.mark.asyncio
async def test_repeated_identical_failure_is_blocked_until_it_works(session):
    book = LessonBook(session)
    args = {"option_id": 1, "units": {"spear": 1}, "reason": "x"}

    assert await book.blocked("send_scavenge", args) is None

    for _ in range(2):
        await book.action("raider", "send_scavenge", args, False, "A coleta deve consistir em pelo menos 10 população.")

    assert "aprendido" in (await book.blocked("send_scavenge", {**args, "reason": "outro"}) or "")
    assert await book.blocked("send_scavenge", {**args, "units": {"spear": 12}}) is None

    await book.action("raider", "send_scavenge", args, True, "ok")
    assert await book.blocked("send_scavenge", args) is None


@pytest.mark.asyncio
async def test_rules_quests_and_notices_are_stored_and_summarized(session):
    book = LessonBook(session)

    await book.action("raider", "send_scavenge", {}, False, "A coleta deve consistir em pelo menos 10 população.")
    await book.notices("recruit_knight", ["Recrutamento iniciado"])
    await book.quest("1400", "Um nome digno", "new", [{"title": "Altere o nome da sua aldeia"}], "No Edifício Principal...")
    await book.quest("1400", "Um nome digno", "finished", [{"title": "Altere o nome da sua aldeia"}], "")
    await session.commit()

    repo = LessonRepository(session)
    quest = await repo.get("quest:1400")
    assert quest is not None and '"finished_at"' in quest.data

    summary = await book.summary()
    assert "send_scavenge" in summary and "Recrutamento iniciado" in summary


@pytest.mark.asyncio
async def test_reports_teach_target_results(session):
    from tribal_assistant.client.scraper.game import ReportSnapshot

    book = LessonBook(session)
    reports = [
        ReportSnapshot("1", "ataca", "attack", "green", False, None, "482|754", "480|750", 30, 20, 10, 60),
        ReportSnapshot("2", "ataca", "attack", "red", False, None, "482|754", "480|750", 0, 0, 0, 0),
    ]
    await book.reports(reports, set())

    target = await book.target("480|750")
    assert target["attacks"] == 2 and target["last_result"] == "red" and target["avg_haul"] == 30


@pytest.mark.asyncio
async def test_learned_refusal_does_not_count_as_a_new_failure(session):
    book = LessonBook(session)
    args = {"option_id": 3, "reason": "x"}

    for _ in range(2):
        await book.action("infrastructure", "unlock_scavenge", args, False, "recursos insuficientes: wood")

    refusal = await book.blocked("unlock_scavenge", args)
    await book.action("infrastructure", "unlock_scavenge", args, False, refusal)

    row = await LessonRepository(session).get(f"attempt:{book.signature('unlock_scavenge', args)}")
    assert row.failed == 2
    assert "aprendido" not in row.text
