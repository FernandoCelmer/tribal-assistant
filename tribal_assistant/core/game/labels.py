"""Portuguese names of the buildings, in the order the game lists them."""

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


def label(name: str) -> str:
    return BUILDING_LABELS.get(name, name)
