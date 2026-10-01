from datetime import UTC, datetime, timedelta

from tribal_assistant.core.agents.clock import Clock

NOW = datetime(2026, 10, 1, 18, 0, tzinfo=UTC)


def test_moments_read_as_server_time_and_distance() -> None:
    clock = Clock(NOW)

    assert clock.header() == "Agora: 01/10 15:00 (hora do servidor)"
    assert clock.when(NOW + timedelta(minutes=58)) == "15:58 (em 58 min)"
    assert clock.when(NOW + timedelta(hours=10)) == "amanhã 01:00 (em 10h00)"
    assert clock.relative((NOW - timedelta(hours=2, minutes=5)).replace(tzinfo=None)) == "há 2h05"
    assert clock.relative("2026-10-01T17:59:40") == "agora"
    assert clock.relative(None) == ""


def test_game_blockers_gain_how_far_they_are() -> None:
    clock = Clock(NOW)

    assert clock.annotate("Recursos disponíveis hoje às 16:36") == "Recursos disponíveis hoje às 16:36 (em 1h36)"
    assert clock.annotate("O Armazém é muito pequeno") == "O Armazém é muito pequeno"


def test_header_shows_sync_age_and_protection_end() -> None:
    clock = Clock(NOW)

    header = clock.header(NOW - timedelta(minutes=3), "2026-10-03T23:38:21+00:00")

    assert "estado lido do jogo há 3 min" in header
    assert "proteção de iniciante até 03/10 20:38 (em 2d5h)" in header
