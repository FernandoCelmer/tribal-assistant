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


def test_own_offer_splits_the_gap_and_keeps_a_floor():
    assert EconomyProposer.own_offer({"wood": 300, "stone": 1500, "iron": 700}, 2285) == ("stone", "wood", 600)
    assert EconomyProposer.own_offer({"wood": 800, "stone": 1000, "iron": 900}, 2285) is None


def test_skill_books_are_used():
    book = {"key": "4001_0", "name": "Livro de Habilidades: Motivação", "detail": "", "usable": True}
    assert UpkeepProposer.item_decision(book, {"wood": 0, "clay": 0, "iron": 0}, 2285, building=False)


def test_reward_label_resources():
    from tribal_assistant.agents.roles.quartermaster import QuartermasterAgent

    assert QuartermasterAgent.reward_resources("Poço de argila 5 150 150 100   Tudo") == (150, 150, 100)
    assert QuartermasterAgent.reward_resources("Mercado 1 1.000 1.200 1.000 Tudo") == (1000, 1200, 1000)


def test_squad_is_sized_by_expected_haul_and_uses_the_paladin():
    from tribal_assistant.agents.proposers.attack import AttackProposer

    assert AttackProposer.squad({"light": 10, "spear": 30}, 200) == {"light": 3}
    assert AttackProposer.squad({"knight": 1, "spear": 30}, 300) == {"knight": 1, "spear": 8}
    assert AttackProposer.squad({"spear": 2}, 300) is None


def test_scavenging_is_split_with_at_least_ten_pop_each():
    from tribal_assistant.agents.proposers.attack import AttackProposer

    parts = AttackProposer.split({"spear": 30, "sword": 10}, {1: 0.1, 2: 0.25})
    assert set(parts) == {1, 2}
    assert sum(parts[1].values()) > sum(parts[2].values())
    assert len(AttackProposer.split({"spear": 13}, {1: 0.1, 2: 0.25})) == 1


def test_mine_follows_the_resource_that_blocks_builds():
    from tests.agents.builders import building, context
    from tribal_assistant.agents.proposers.infrastructure import InfrastructureProposer

    class View:
        pass

    ctx = context(buildings=[building("main", 7, cost=600), building("wood", 7), building("stone", 7), building("iron", 7), building("storage", 5), building("farm", 5)], stock=300)
    ctx.stock = {"wood": 100, "clay": 900, "iron": 900}
    ctx.village.wood_prod, ctx.village.clay_prod, ctx.village.iron_prod = 160, 130, 110

    from tribal_assistant.agents.coordination.estimates import Estimator

    view = View()
    view.ctx = ctx
    view.estimator = Estimator(ctx)
    view.build_cost = lambda b: {"wood": ctx.building(b).next_wood, "clay": ctx.building(b).next_clay, "iron": ctx.building(b).next_iron} if ctx.building(b) else {}

    assert InfrastructureProposer.bottleneck(view, ["main"]) == "wood"


def test_twenty_swordsmen_fill_two_scavenging_tiers():
    from tribal_assistant.agents.proposers.attack import AttackProposer

    parts = AttackProposer.split({"sword": 20}, {1: 0.1, 2: 0.25})
    assert set(parts) == {1, 2}
    assert parts[1]["sword"] + parts[2]["sword"] == 20


def test_iron_surplus_buys_wood_when_wood_is_almost_gone():
    offer = {"receive": "wood", "receive_amount": 1000, "pay": "iron", "pay_amount": 1000, "player": "a", "minutes": 120, "can_accept": True}

    assert EconomyProposer.pick_offer([offer], {"wood": 20, "stone": 400, "iron": 1500}, 4247) == offer
    assert EconomyProposer.pick_offer([offer], {"wood": 900, "stone": 400, "iron": 1500}, 4247) is None
