from sqlalchemy.ext.asyncio import AsyncSession

from tests.agents.builders import building, context
from tribal_assistant.core.agents.coordination.account import FAR, AccountRoles, VillageFacts
from tribal_assistant.core.agents.coordination.roles import RoleSelector
from tribal_assistant.core.agents.coordination.strategy import Role
from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.models.world import WorldPlayer, WorldVillage
from tribal_assistant.core.repositories.coordination import CoordinationRepository


def _facts(village_id: int, exposure: float, *, dangerous: bool = False, stable: int = 0, academy: int = 0) -> VillageFacts:
    return VillageFacts(village_id, f"Aldeia {village_id}", exposure, dangerous, stable, academy)


def test_three_villages_split_defense_expansion_and_offensive() -> None:
    roles = AccountRoles.assign([_facts(1, 3, dangerous=True, stable=2), _facts(2, 10, academy=1, stable=1), _facts(3, 20, stable=3)])

    assert {k: v[0] for k, v in roles.items()} == {1: Role.DEFENSE, 2: Role.EXPANSION, 3: Role.OFFENSIVE}


def test_two_villages_exposed_one_supports_and_far_stable_raids() -> None:
    roles = AccountRoles.assign([_facts(1, 5, stable=1), _facts(2, FAR, stable=1)])

    assert roles[1][0] == Role.SUPPORT
    assert roles[2][0] == Role.OFFENSIVE and "sem jogadores" in roles[2][1]


def test_calm_account_without_buildings_keeps_each_village_on_its_own() -> None:
    assert AccountRoles.assign([_facts(1, FAR), _facts(2, 30)]) == {}
    assert AccountRoles.assign([_facts(1, 1, dangerous=True)]) == {}


def test_account_parameters_are_knobs() -> None:
    facts = [_facts(1, 12, stable=1), _facts(2, 30)]

    assert AccountRoles.assign(facts)[1][0] == Role.OFFENSIVE
    assert AccountRoles.assign(facts, Knobs({"account.exposed_distance": 15}))[1][0] == Role.SUPPORT
    assert AccountRoles.assign([_facts(1, FAR, stable=1), _facts(2, FAR)], Knobs({"account.offensive_stable": 2})) == {}


def test_own_alarm_and_a_lonely_academy_path_win_over_the_account() -> None:
    roles = {1: (Role.OFFENSIVE, "longe"), 2: (Role.SUPPORT, "exposta")}

    assert AccountRoles.merge(Role.DEFENSE, "perigo", roles[1], roles) == (Role.DEFENSE, "perigo")
    assert AccountRoles.merge(Role.EXPANSION, "academia", roles[1], roles) == (Role.EXPANSION, "academia")
    assert AccountRoles.merge(Role.GROWTH, "produção", roles[1], roles)[0] == Role.OFFENSIVE
    assert AccountRoles.merge(Role.EXPANSION, "academia", roles[1], roles | {3: (Role.EXPANSION, "outra")})[0] == Role.OFFENSIVE


def _village(village_id: int, coords: str, buildings=None):
    ctx = context(buildings=buildings or [building("main", 5)])
    ctx.village.id = village_id
    ctx.village.coords = coords
    ctx.village.name = f"Aldeia {village_id}"
    ctx.player = {"name": "Eu"}
    return ctx


async def test_selector_shares_roles_out_and_keeps_the_hysteresis(session: AsyncSession) -> None:
    session.add_all([WorldPlayer(id=77, name="Vizinho", ally_id=0, points=50, villages=1, rank=1), WorldVillage(id=9, name="V", x=502, y=500, player_id=77, points=50)])
    await session.commit()

    front = _village(1, "500|500")
    academy = _village(2, "520|520", [building("main", 20), building("snob", 1)])
    raider = _village(3, "540|540", [building("main", 10), building("stable", 3)])
    siblings = [front, academy, raider]
    selector = RoleSelector(session, Knobs())
    repo = CoordinationRepository(session)

    assert (await selector.select(front, siblings))[0] == Role.SUPPORT
    assert (await selector.select(academy, siblings))[0] == Role.EXPANSION
    assert (await selector.select(raider, siblings))[0] == Role.OFFENSIVE
    assert (await repo.strategy(3)).role == "offensive"

    await repo.set_strategy(3, "growth", "antes", manual=False)
    first = await selector.select(raider, siblings)
    second = await selector.select(raider, siblings)
    third = await selector.select(raider, siblings)
    assert (first[0], second[0], third[0]) == (Role.GROWTH, Role.GROWTH, Role.OFFENSIVE)

    alone = await RoleSelector(session, Knobs()).select(_village(4, "560|560", [building("stable", 3)]))
    assert alone[0] == Role.GROWTH
