from datetime import datetime, timedelta

from tests.agents.builders import building, context, scavenge, unit
from tribal_assistant.core.agents.coordination.budget import Budget, Reservation
from tribal_assistant.core.agents.coordination.estimates import Estimator
from tribal_assistant.core.agents.coordination.proposal import Proposal
from tribal_assistant.core.agents.market import MarketRule
from tribal_assistant.core.agents.proposers.attack import AttackProposer
from tribal_assistant.core.agents.proposers.economy import EconomyProposer
from tribal_assistant.core.agents.proposers.infrastructure import InfrastructureProposer
from tribal_assistant.core.agents.proposers.recruitment import RecruitmentProposer
from tribal_assistant.core.agents.proposers.upkeep import UpkeepProposer
from tribal_assistant.core.agents.roles.quartermaster import QuartermasterAgent


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
    assert EconomyProposer.own_offer({"wood": 900, "stone": 1000, "iron": 950}, 2285) is None


def test_small_surplus_still_trades_in_lots_of_a_hundred():
    stock = {"wood": 406, "stone": 287, "iron": 1119}

    assert EconomyProposer.own_offer(stock, 4247) == ("iron", "stone", 400)
    assert EconomyProposer.own_offer({"wood": 800, "stone": 1000, "iron": 900}, 2285) == ("stone", "wood", 100)


def test_trade_never_flips_the_imbalance():
    stock = {"wood": 406, "stone": 287, "iron": 1119}

    assert MarketRule.refusal(stock, "iron", 400, "stone", 400, 4247) is None
    assert MarketRule.refusal(stock, "iron", 900, "stone", 900, 4247)
    assert MarketRule.refusal(stock, "iron", 1000, "wood", 1000, 4247)


def test_skill_books_are_used():
    book = {"key": "4001_0", "name": "Livro de Habilidades: Motivação", "detail": "", "usable": True}
    assert UpkeepProposer.item_decision(book, {"wood": 0, "clay": 0, "iron": 0}, 2285, building=False)


def test_reward_label_resources():
    assert QuartermasterAgent.reward_resources("Poço de argila 5 150 150 100   Tudo") == (150, 150, 100)
    assert QuartermasterAgent.reward_resources("Mercado 1 1.000 1.200 1.000 Tudo") == (1000, 1200, 1000)


def test_squad_is_sized_by_expected_haul_and_uses_the_paladin():
    assert AttackProposer.squad({"light": 10, "spear": 30}, 200) == {"light": 3}
    assert AttackProposer.squad({"knight": 1, "spear": 30}, 300) == {"knight": 1, "spear": 8}
    assert AttackProposer.squad({"spear": 2}, 300) is None


def test_scavenging_picks_the_tiers_that_yield_most_per_minute():
    tiers = {1: 0.10, 2: 0.25, 3: 0.50, 4: 0.75}
    assert set(AttackProposer.split({"spear": 100}, tiers)) == {2, 3, 4}
    assert set(AttackProposer.split({"spear": 1000}, tiers)) == {1, 2, 3, 4}
    assert set(AttackProposer.split({"spear": 12}, tiers)) == {4}


def test_scavenging_split_makes_every_run_end_together():
    parts = AttackProposer.split({"spear": 1040}, {1: 0.10, 2: 0.25, 3: 0.50, 4: 0.75})
    assert [parts[t]["spear"] for t in (1, 2, 3, 4)] == [600, 240, 120, 80]
    assert all(sum(p.values()) >= 10 for p in parts.values())


def test_mine_follows_the_resource_that_blocks_builds():
    class View:
        pass

    ctx = context(buildings=[building("main", 7, cost=600), building("wood", 7), building("stone", 7), building("iron", 7), building("storage", 5), building("farm", 5)], stock=300)
    ctx.stock = {"wood": 100, "clay": 900, "iron": 900}
    ctx.village.wood_prod, ctx.village.clay_prod, ctx.village.iron_prod = 160, 130, 110

    view = View()
    view.ctx = ctx
    view.estimator = Estimator(ctx)
    view.build_cost = lambda b: {"wood": ctx.building(b).next_wood, "clay": ctx.building(b).next_clay, "iron": ctx.building(b).next_iron} if ctx.building(b) else {}

    assert InfrastructureProposer.bottleneck(view, ["main"]) == "wood"


def test_iron_surplus_buys_wood_when_wood_is_almost_gone():
    offer = {"receive": "wood", "receive_amount": 1000, "pay": "iron", "pay_amount": 1000, "player": "a", "minutes": 120, "can_accept": True}

    assert EconomyProposer.pick_offer([offer], {"wood": 20, "stone": 400, "iron": 1500}, 4247) == offer
    assert EconomyProposer.pick_offer([offer], {"wood": 900, "stone": 400, "iron": 1500}, 4247) is None


def test_farm_is_built_before_population_locks():
    start = datetime(2026, 9, 29, 12)
    growing = [(start, 200), (start + timedelta(hours=2), 260)]
    assert EconomyProposer.pop_lock_hours(growing, 90) == 3.0
    assert EconomyProposer.pop_lock_hours([(start, 200), (start + timedelta(hours=2), 200)], 90) == float("inf")
    assert EconomyProposer.pop_lock_hours(growing[:1], 90) == float("inf")


def test_scavenging_army_grows_with_the_farm():
    assert RecruitmentProposer.scavenge_target(854) == 341
    assert RecruitmentProposer.scavenge_target(24000) == 1000


def test_unit_bonus_items_wait_for_an_incoming_attack():
    sword = {"key": "3040_0", "name": "Bônus de espadachim", "detail": "Espadachim: +5% poder de ataque e defesa", "usable": True}
    stock = {"wood": 300, "clay": 400, "iron": 700}
    assert UpkeepProposer.item_decision(sword, stock, 5222, False) is None
    assert UpkeepProposer.item_decision(sword, stock, 5222, False, attacked=True, home={"sword": 40})
    assert UpkeepProposer.item_decision(sword, stock, 5222, False, attacked=True, home={"sword": 5}) is None


def test_next_build_reservation_lets_small_recruit_batches_through_while_the_queue_runs():
    ctx = context(stock=500)
    budget = Budget(ctx)
    budget.reserve(Reservation("plan:barracks", "operation", "próxima obra", {"wood": 500, "clay": 500, "iron": 500}, exempt=("recruit_units",)))

    assert budget.affordable({"wood": 250, "clay": 150, "iron": 50}, "scavenge", "recruit_units")
    assert not budget.affordable({"wood": 250, "clay": 150, "iron": 50}, "", "upgrade_building")


async def test_vetoed_raids_do_not_hold_troops_back_from_scavenging():
    class View:
        pass

    view = View()
    view.ctx = context(units=[unit("spear", 14), unit("sword", 20)], scavenge_options=[scavenge(1), scavenge(2)])
    view.dry_run = False
    view.role = None
    notes = []
    view.note = notes.append
    proposer = AttackProposer()

    async def raids(_view):
        return [Proposal("attack", "send_farm_attack", {"target": "1|1"}, "saque", "", troops={"spear": 14, "sword": 13}, confidence=0.2)]

    proposer._raids = raids
    items = await proposer.propose(view)
    sent = [p for p in items if p.action == "send_scavenge"]
    assert sent and sum(sum(p.troops.values()) for p in sent) == 34


def test_idle_queue_takes_the_cheapest_pit_that_fits_when_the_plan_is_far():
    class Guard:
        @staticmethod
        def check_upgrade(ctx, name):
            return None

    class View:
        pass

    ctx = context(buildings=[building("barracks", 4, cost=900), building("wood", 11, cost=300), building("stone", 10, cost=250), building("iron", 7, cost=200)], stock=400)
    view = View()
    view.ctx = ctx
    view.guard = Guard()
    view.estimator = Estimator(ctx)
    view.build_cost = lambda b: {"wood": ctx.building(b).next_wood, "clay": ctx.building(b).next_clay, "iron": ctx.building(b).next_iron} if ctx.building(b) else {}

    assert InfrastructureProposer.filler(view, ["barracks"]) == "stone"

    busy = context(buildings=[building("barracks", 4, cost=900), building("stone", 10, cost=250), building("smith", 3, queued_level=4)], stock=400)
    view.ctx = busy
    view.estimator = Estimator(busy)
    assert InfrastructureProposer.filler(view, ["barracks"]) is None


def test_base_reserve_never_swallows_the_whole_stock():
    assert EconomyProposer.base_reserve(5222, 0.1, {"wood": 495, "clay": 386, "iron": 446}, 0.25) == {"wood": 123, "clay": 96, "iron": 111}
    assert EconomyProposer.base_reserve(5222, 0.1, {"wood": 4000, "clay": 4000, "iron": 4000}, 0.25) == {"wood": 522, "clay": 522, "iron": 522}


def test_profile_quest_is_detected_until_finished():
    from tribal_assistant.core.agents.proposers.upkeep import UpkeepProposer

    quest = {"id": "1500", "title": "A aparência importa", "goals": [{"title": "Altere o texto do seu perfil"}]}
    assert UpkeepProposer.profile_quest([quest])
    assert not UpkeepProposer.profile_quest([{**quest, "finished": True}])
    assert not UpkeepProposer.profile_quest([{"id": "1", "title": "Construa o quartel"}])


async def test_profile_text_comes_from_the_model_and_is_skipped_without_it():
    from tribal_assistant.core.agents.writer import ProfileWriter
    from tribal_assistant.core.ai.types import Reply

    class Chat:
        async def send(self, results=None):
            return Reply(text='"Jogo com calma no br144 e gosto de ajudar a tribo."')

    class Llm:
        def conversation(self, system, prompt, tools):
            assert "Frenor" in prompt
            return Chat()

    class Factory:
        def __init__(self, llm):
            self.llm = llm

        def build(self):
            return self.llm

    facts = ProfileWriter.facts({"name": "Frenor", "world": "br144", "points": 300}, 1, "growth", None)
    assert await ProfileWriter(Factory(Llm())).write(facts) == "Jogo com calma no br144 e gosto de ajudar a tribo."
    assert await ProfileWriter(Factory(None)).write(facts) is None
