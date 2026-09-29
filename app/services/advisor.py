"""Upgrade advisor — pure rules over the synced village state.

Not a full build order: a handful of rules that catch the usual bottlenecks
(population, storage, resource production) and fall back to the cheapest
upgrade available right now.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.models.building import Building
from app.models.village import Village

BUILDING_LABELS = {
    "main": "Edifício principal",
    "barracks": "Quartel",
    "stable": "Estábulo",
    "garage": "Oficina",
    "church": "Igreja",
    "church_f": "Primeira igreja",
    "watchtower": "Torre de vigia",
    "snob": "Academia",
    "smith": "Ferreiro",
    "place": "Praça de reunião",
    "statue": "Estátua",
    "market": "Mercado",
    "wood": "Bosque",
    "stone": "Poço de argila",
    "iron": "Mina de ferro",
    "farm": "Fazenda",
    "storage": "Armazém",
    "hide": "Esconderijo",
    "wall": "Muralha",
}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

FULL_RATIO = 0.85
MAIN_TARGET_LEVEL = 20
WALL_UNDER_ATTACK_LEVEL = 10
RESOURCE_BUILDINGS = ("wood", "stone", "iron")


@dataclass(frozen=True)
class Recommendation:
    building: str
    label: str
    from_level: int
    to_level: int
    wood: int
    clay: int
    iron: int
    pop: int
    build_time: int | None
    can_build: bool
    blocker: str | None
    eta_seconds: int | None
    priority: str
    reason: str


def label(name: str) -> str:
    return BUILDING_LABELS.get(name, name)


def _eta_seconds(village: Village, b: Building) -> int | None:
    """Seconds until the village can afford `b`, from current stock and production."""
    worst = 0.0
    for cost, stock, per_hour in (
        (b.next_wood or 0, village.wood, village.wood_prod),
        (b.next_clay or 0, village.clay, village.clay_prod),
        (b.next_iron or 0, village.iron, village.iron_prod),
    ):
        missing = cost - stock
        if missing <= 0:
            continue
        if cost > village.storage or per_hour <= 0:
            return None
        worst = max(worst, missing / per_hour * 3600)
    return int(worst)


def _upgradable(b: Building | None) -> bool:
    return b is not None and b.next_level is not None and b.blocker != "nível máximo"


def recommend(
    village: Village,
    buildings: Sequence[Building],
    incomings: int = 0,
    now: datetime | None = None,
) -> list[Recommendation]:
    by_name = {b.name: b for b in buildings}
    picked: dict[str, tuple[str, str]] = {}

    def suggest(name: str, priority: str, reason: str) -> None:
        if name in picked or not _upgradable(by_name.get(name)):
            return
        picked[name] = (priority, reason)

    if village.pop_max and village.pop_current / village.pop_max >= FULL_RATIO:
        pct = round(village.pop_current / village.pop_max * 100)
        suggest("farm", "high", f"População em {pct}% da fazenda")

    if village.storage:
        fullest = max(village.wood, village.clay, village.iron) / village.storage
        if fullest >= FULL_RATIO:
            suggest("storage", "high", f"Armazém {round(fullest * 100)}% cheio, recurso vai sobrar")
        too_expensive = [
            b for b in buildings
            if _upgradable(b)
            and max(b.next_wood or 0, b.next_clay or 0, b.next_iron or 0) > village.storage
        ]
        if too_expensive:
            names = ", ".join(label(b.name) for b in too_expensive[:3])
            suggest("storage", "high", f"Armazém pequeno demais para: {names}")

    if incomings:
        wall = by_name.get("wall")
        if wall is not None and wall.level < WALL_UNDER_ATTACK_LEVEL:
            suggest("wall", "high", f"{incomings} ataque(s) a caminho e muralha nível {wall.level}")

    pits = [by_name[n] for n in RESOURCE_BUILDINGS if _upgradable(by_name.get(n))]
    if pits:
        lowest = min(pits, key=lambda b: b.level)
        suggest(lowest.name, "medium", "Recurso com menor nível: mais produção por hora")

    main = by_name.get("main")
    if main is not None and main.level < MAIN_TARGET_LEVEL:
        suggest("main", "medium", "Edifício principal acelera todas as construções")

    affordable = [
        b for b in buildings if _upgradable(b) and b.can_build and b.name not in picked
    ]
    if affordable:
        cheapest = min(
            affordable, key=lambda b: (b.next_wood or 0) + (b.next_clay or 0) + (b.next_iron or 0)
        )
        suggest(cheapest.name, "low", "Mais barato disponível agora")

    recommendations = []
    for name, (priority, reason) in picked.items():
        b = by_name[name]
        recommendations.append(
            Recommendation(
                building=name,
                label=label(name),
                from_level=(b.next_level or b.level + 1) - 1,
                to_level=b.next_level or b.level + 1,
                wood=b.next_wood or 0,
                clay=b.next_clay or 0,
                iron=b.next_iron or 0,
                pop=b.next_pop or 0,
                build_time=b.build_time,
                can_build=b.can_build,
                blocker=b.blocker,
                eta_seconds=0 if b.can_build else _eta_seconds(village, b),
                priority=priority,
                reason=reason,
            )
        )
    recommendations.sort(
        key=lambda r: (PRIORITY_ORDER[r.priority], r.eta_seconds if r.eta_seconds is not None else 1e12)
    )
    return recommendations
