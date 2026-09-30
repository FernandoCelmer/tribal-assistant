from tribal_assistant.core.agents.target_intel import TargetIntel
from tribal_assistant.core.game.scraper.game import parse_reports

TITLE = "Frenor (Frenor 001 (482|754) K74) exploradores Aldeia-bonus (487|757) K74"


def test_scout_report_takes_category_and_coords_from_the_title():
    [report] = parse_reports([{"id": "1", "title": TITLE, "icons": "blue", "received": ""}])

    assert report.category == "scout"
    assert (report.origin_coords, report.target_coords) == ("482|754", "487|757")


def test_scout_report_teaches_the_target_without_counting_a_raid():
    [report] = parse_reports([{"id": "1", "title": TITLE, "icons": "blue", "received": ""}])
    data = TargetIntel.merge({"attacks": 2, "total_haul": 300, "avg_haul": 150}, report, {})

    assert data["last_probe"] == report.result and data["attacks"] == 2 and data["avg_haul"] == 150
