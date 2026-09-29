from tribal_assistant.agents.proposers.economy import EconomyProposer
from tribal_assistant.agents.proposers.upkeep import UpkeepProposer


def test_best_flag_prefers_production_then_population():
    assert UpkeepProposer.best_flag([(3, 1), (6, 3), (1, 1)]) == (1, 1)
    assert UpkeepProposer.best_flag([(3, 1), (6, 1), (6, 3)]) == (6, 3)
    assert UpkeepProposer.best_flag([]) is None


def test_training_only_spends_real_surplus():
    assert UpkeepProposer.training({"wood": 300, "clay": 800, "iron": 350}, 2285) is None
    assert UpkeepProposer.training({"wood": 450, "clay": 800, "iron": 500}, 2285) == 21
    assert UpkeepProposer.training({"wood": 4200, "clay": 4500, "iron": 4100}, 5000) == 25


def test_items_use_construction_bonus_while_building_and_packs_only_when_they_fit():
    bonus = {"key": "3057_0", "name": "Bônus em Construção", "detail": "construção +10%", "usable": True}
    pack = {"key": "1001_0", "name": "Pacote", "detail": "Adiciona 10% da capacidade do seu armazém", "usable": True}
    stock = {"wood": 1000, "clay": 1000, "iron": 1000}

    assert UpkeepProposer.item_decision(bonus, stock, 2285, building=True)
    assert UpkeepProposer.item_decision(bonus, stock, 2285, building=False) is None
    assert UpkeepProposer.item_decision(pack, stock, 2285, building=True) is None
    assert UpkeepProposer.item_decision(pack, stock, 8000, building=True)
    assert UpkeepProposer.item_decision(pack, {"wood": 7900, "clay": 1, "iron": 1}, 8000, building=True) is None


def test_market_offer_only_trades_surplus_for_the_lowest_resource():
    stock = {"wood": 400, "stone": 2100, "iron": 500}
    offers = [
        {"receive": "wood", "receive_amount": 1000, "pay": "stone", "pay_amount": 1000, "player": "a", "minutes": 331, "can_accept": True},
        {"receive": "iron", "receive_amount": 1000, "pay": "stone", "pay_amount": 1000, "player": "b", "minutes": 157, "can_accept": True},
        {"receive": "wood", "receive_amount": 800, "pay": "stone", "pay_amount": 1000, "player": "c", "minutes": 10, "can_accept": True},
    ]

    assert EconomyProposer.pick_offer(offers, stock, 3000)["player"] == "a"
    assert EconomyProposer.pick_offer(offers, {"wood": 400, "stone": 850, "iron": 360}, 2285) is None
