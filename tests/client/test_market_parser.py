from pathlib import Path

from tribal_assistant.core.game.market import OwnOfferParser

HTML = Path(__file__).resolve().parents[1] / "fixtures" / "html"


def test_own_offer_rows_come_from_the_real_screen() -> None:
    offers = OwnOfferParser.offers((HTML / "market_own_offer_listed.html").read_text())

    assert offers == [
        {"id": "165611", "sell": "iron", "sell_amount": 100, "buy": "wood", "buy_amount": 100, "count": 1, "max_hours": 5, "village": None}
    ]


def test_screens_without_offers_list_nothing() -> None:
    assert OwnOfferParser.offers((HTML / "market_own_offer.html").read_text()) == []
    assert OwnOfferParser.offers((HTML / "market_all_offers.html").read_text()) == []


def test_ratio_limits_and_merchants_are_read_from_the_page() -> None:
    html = (HTML / "market_own_offer_listed.html").read_text()

    assert OwnOfferParser.ratio(html) == (0.9, 1.1)
    assert OwnOfferParser.merchants(html) == {"free": 2, "total": 5, "carry": 1000}
    assert OwnOfferParser.ratio("<p>sem mercado</p>") == (0.9, 1.1)


def test_parked_offer_asks_more_than_it_gives() -> None:
    row = """<table id="own_offers_table"><tr class="offer_container" data-id="7" data-count="3">
      <td><input name="id_7" type="checkbox"></td>
      <td><span class="icon header iron"></span>1.000</td>
      <td><span class="icon header stone"></span>1.100</td>
      <td>3</td><td>hoje</td><td><span id="offerText_7">1 horas</span></td><td>Público</td></tr></table>"""

    offer = OwnOfferParser.offers(row)[0]
    assert (offer["sell"], offer["sell_amount"], offer["buy"], offer["buy_amount"], offer["count"], offer["max_hours"]) == ("iron", 1000, "stone", 1100, 3, 1)
