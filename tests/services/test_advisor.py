from tribal_assistant.models.building import Building
from tribal_assistant.models.village import Village
from tribal_assistant.services.advisor import recommend


def _village(**overrides: int) -> Village:
    values = dict(name="v", coords="1|1", wood=500, clay=500, iron=500, storage=1000,
                  pop_current=10, pop_max=100, wood_prod=100, clay_prod=100, iron_prod=100)
    values.update(overrides)
    return Village(**values)


def _building(name: str, level: int, cost: int = 100, can_build: bool = True) -> Building:
    return Building(name=name, level=level, next_level=level + 1, max_level=30,
                    next_wood=cost, next_clay=cost, next_iron=cost, next_pop=1,
                    build_time=60, can_build=can_build)


def test_full_farm_is_top_priority() -> None:
    village = _village(pop_current=95, pop_max=100)
    recs = recommend(village, [_building("farm", 3), _building("wood", 5)])
    assert recs[0].building == "farm" and recs[0].priority == "high"


def test_lowest_resource_pit_is_suggested() -> None:
    buildings = [_building("wood", 5), _building("stone", 2), _building("iron", 4)]
    recs = recommend(_village(), buildings)
    assert any(r.building == "stone" and r.priority == "medium" for r in recs)


def test_eta_uses_production() -> None:
    village = _village(wood=0, clay=0, iron=0)
    (rec,) = [r for r in recommend(village, [_building("wood", 1, cost=200, can_build=False)])
              if r.building == "wood"]
    assert rec.eta_seconds == 2 * 3600


def test_storage_when_upgrade_exceeds_capacity() -> None:
    buildings = [_building("storage", 2), _building("main", 5, cost=5000, can_build=False)]
    recs = recommend(_village(), buildings)
    assert recs[0].building == "storage"
