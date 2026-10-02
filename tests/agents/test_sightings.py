from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.coordination.threat import Threat, ThreatScan
from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.sightings import Sighting, SightingBook, number


def profile(points: str, coords: list[str]) -> Sighting:
    return Sighting("info_player", {"id": "77"}, "perfil de Doris", {"Pontos": points, "Tribo": "ABC"}, coords)


def test_numbers_read_like_the_game_writes_them() -> None:
    assert number("12.345") == 12345
    assert number("Rank 7") == 7
    assert number("") is None
    assert number("53 . 382") == 53382
    assert number("10,553") == 10553


def test_the_real_tribe_page_reads_members_and_open_door() -> None:
    page = Sighting("info_ally", {"id": "1"}, "tribo [OMG]", {"Número de membros": "42", "Total de pontos": "53 . 382"}, [], "Propriedades Junte-se agora! Descrição")

    found = SightingBook.findings(page, {}, 0, Knobs())[0]

    assert found.data["members"] == 42 and found.data["recruiting"]


def test_a_neighbour_who_took_a_village_is_flagged_expanding() -> None:
    before = profile("1.000", ["480|750"]).snapshot(datetime(2026, 10, 1))
    found = SightingBook.findings(profile("1.400", ["480|750", "483|755"]), before, 10, Knobs())

    texts = [f.text for f in found]
    assert "Doris ganhou aldeia(s) 483|755 em 10h00" in texts
    assert "Doris: 1000→1400 pontos (+40/h)" in texts
    assert any(f.data.get("expanding_at") for f in found)


def test_a_neighbour_stuck_on_the_same_points_reads_as_inactive() -> None:
    before = profile("900", ["480|750"]).snapshot(datetime(2026, 10, 1))

    found = SightingBook.findings(profile("900", ["480|750"]), before, 30, Knobs())

    assert found[0].text == "Doris parado em 900 pontos há 30h00: provável inativo"


def test_a_tribe_page_says_whether_it_recruits() -> None:
    open_tribe = Sighting("info_ally", {"id": "9"}, "tribo [ABC]", {"Membros": "41"}, [], "Estamos recrutando jogadores ativos!")
    closed = Sighting("info_ally", {"id": "9"}, "tribo [ABC]", {"Membros": "41"}, [], "Não aceitamos candidaturas.")

    assert SightingBook.findings(open_tribe, {}, 0, Knobs())[0].data["recruiting"]
    assert SightingBook.findings(closed, {}, 0, Knobs())[0].data["closed"]


def test_other_pages_report_the_numbers_that_moved() -> None:
    stats = Sighting("info_player", {"mode": "stats_own"}, "estatísticas", {"Saqueado": "5.000", "Ataques": "12"})
    before = {"pairs": {"Saqueado": "3.000", "Ataques": "12"}}

    assert SightingBook.findings(stats, before, 2, Knobs())[0].text == "estatísticas: Saqueado 3.000→5.000"


async def test_learning_a_tour_feeds_the_threat_scan(session: AsyncSession) -> None:
    book = SightingBook(session)
    first = {"screen": "info_player", "params": {"id": "77"}, "label": "perfil de Doris", "pairs": {"Pontos": "100"}, "coords": ["480|750"]}
    await book.learn([first], Knobs())
    notes, new = await book.learn([{**first, "coords": ["480|750", "481|751"]}], Knobs())

    assert notes and "ganhou aldeia" in notes[0] and new == 0
    assert "77" in await book.expanding(48)

    scan = ThreatScan(session)
    scan.expanding = {"77"}
    weak = Threat("Doris", 100, 3.0, "77")
    assert scan.dangerous([weak], own_points=5000) == [weak]


def test_the_map_tooltip_is_not_a_finding() -> None:
    tooltip = Sighting("map", {}, "mapa ao redor", {"Pontos": "26"})

    assert SightingBook.findings(tooltip, {"pairs": {"Pontos": "243"}}, 1, Knobs()) == []
