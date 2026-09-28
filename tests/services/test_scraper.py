from app.bot.scraper.village import scrape_village

HTML = """
<html><body>
<div id="menu_row2_village"><a><span>MinhaAldeia</span></a><span class="coord">500|500</span></div>
<span id="wood">1.234</span>
<span id="stone">2345</span>
<span id="iron">3.456</span>
<span id="storage">10000</span>
<span id="pop_current_label">24</span>
<span id="pop_max_label">240</span>
</body></html>
"""


def test_scrape_village_parses_all_fields() -> None:
    snap = scrape_village(HTML)
    assert snap.name == "MinhaAldeia"
    assert snap.coords == "500|500"
    assert snap.wood == 1234
    assert snap.clay == 2345
    assert snap.iron == 3456
    assert snap.storage == 10000
    assert snap.pop_current == 24
    assert snap.pop_max == 240
