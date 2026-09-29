from pathlib import Path

from tribal_assistant.client.scraper.quests import parse_quest_body, parse_quest_list, parse_rewards

HTML = (Path(__file__).parents[1] / "fixtures" / "html" / "quests.html").read_text(encoding="utf-8")


def test_quest_list_reads_every_line() -> None:
    quests = parse_quest_list(HTML)

    assert [q.quest_id for q in quests] == ["1040", "1210", "1500", "1925"]
    assert quests[0].title == "Aumentar produção"
    assert quests[0].state == "progress"
    assert quests[2].state == "new"


def test_open_quest_goals_and_progress() -> None:
    description, goals, can_complete = parse_quest_body(HTML)

    assert description.startswith("Se você tem recursos")
    assert [(g.title, g.current, g.target) for g in goals] == [
        ("Melhore Bosque", 4, 5),
        ("Melhore Poço de argila", 4, 5),
        ("Melhore Mina de ferro", 1, 3),
    ]
    assert not can_complete
    assert not goals[0].done


def test_claimable_rewards() -> None:
    rewards = parse_rewards(HTML)

    assert [r.reward_id for r in rewards] == ["10820981", "10820101"]
    assert "Poço de argila" in rewards[0].label
