from types import SimpleNamespace

from tribal_assistant.core.agents.coordination.proposal import Factors, Proposal
from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.proposers.infrastructure import InfrastructureProposer


def build(name: str, cost: int, impact: float) -> Proposal:
    return Proposal("infrastructure", "upgrade_building", {"building": name}, "", cost={"wood": cost, "clay": cost, "iron": cost}, factors=Factors(impact=impact))


def test_only_the_strongest_build_that_does_not_fit_stays_next_to_those_that_fit():
    view = SimpleNamespace(ctx=SimpleNamespace(stock={"wood": 500, "clay": 500, "iron": 500}), knobs=Knobs())
    items = [build("wood", 300, 0.4), build("main", 900, 0.6), build("wall", 800, 0.3), build("storage", 400, 0.2), build("smith", 950, 0.7)]

    kept = [p.arguments["building"] for p in InfrastructureProposer.trim(view, items)]

    assert kept == ["wood", "storage", "smith"]
