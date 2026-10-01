from datetime import UTC, datetime, timedelta

from tribal_assistant.core.agents.absence import Habit, Heartbeat
from tribal_assistant.core.agents.clock import Clock

LEFT = datetime(2026, 10, 1, 1, 0, tzinfo=UTC)


def beat(**extra) -> dict:
    return {
        "at": LEFT.isoformat(),
        "queue_until": (LEFT + timedelta(hours=1)).isoformat(),
        "scavenge_back": (LEFT + timedelta(hours=2)).isoformat(),
        "scavenge_open": 2,
        "recruit_until": None,
        "stock": {"wood": 9000, "clay": 1000, "iron": 1000},
        "storage": 10000,
        "prod": {"wood": 500, "clay": 300, "iron": 300},
        "points": 480,
        **extra,
    }


def test_a_ten_hour_gap_counts_idle_queues_and_spilled_storage() -> None:
    gap = Heartbeat.gap(beat(), LEFT + timedelta(hours=10), 492)

    assert round(gap.hours) == 10
    assert gap.queue_idle == 9
    assert gap.scavenge_idle == 8
    assert gap.recruit_idle == 10
    assert gap.wasted == {"wood": 4000}
    assert gap.full_at == LEFT + timedelta(hours=2)
    assert gap.points == (480, 492)


def test_the_gap_reads_as_one_clear_paragraph() -> None:
    gap = Heartbeat.gap(beat(), LEFT + timedelta(hours=10), 492)
    gap.attacked = 1

    text = gap.describe(Clock(gap.end))

    assert text.startswith("AUSÊNCIA: o bot ficou 10h00 sem jogar")
    assert "fila de obras parada 9h00" in text
    assert "madeira ~4000" in text
    assert "1 ataque(s) contra a aldeia" in text


def test_habit_forecasts_the_usual_night_stop() -> None:
    nights = [
        {"start": datetime(2026, 9, day, 2, 10 + day, tzinfo=UTC).isoformat(), "hours": 9}
        for day in (27, 28, 29)
    ]

    stop, hours, count = Habit(nights, 3).forecast(datetime(2026, 9, 30, 22, 0, tzinfo=UTC))

    assert stop == datetime(2026, 10, 1, 2, 38, tzinfo=UTC)
    assert hours == 9 and count == 3


def test_habit_needs_a_few_long_gaps() -> None:
    short = [{"start": LEFT.isoformat(), "hours": 1}] * 5

    assert Habit(short, 3).forecast(LEFT) is None
