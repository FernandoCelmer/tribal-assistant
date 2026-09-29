"""Game facts taken from docs/help (pt-BR Tribal Wars help pages).

Only what the docs state; unknown prerequisites are left empty and the game's
own "can build" answer stays the final word.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BuildingInfo:
    id: str
    label: str
    max_level: int
    requires: dict[str, int] = field(default_factory=dict)
    role: str = ""


@dataclass(frozen=True)
class UnitInfo:
    id: str
    label: str
    cost: tuple[int, int, int]
    pop: int
    attack: int
    defense: tuple[int, int, int]
    speed: float
    carry: int
    requires: str = ""
    role: str = ""


BUILDINGS: dict[str, BuildingInfo] = {
    b.id: b
    for b in (
        BuildingInfo("main", "Edifício principal", 30, {}, "Constrói e acelera todas as obras; nível 15 libera demolição."),
        BuildingInfo("barracks", "Quartel", 25, {"main": 3}, "Recruta infantaria; níveis altos recrutam mais rápido."),
        BuildingInfo("stable", "Estábulo", 20, {"barracks": 5, "smith": 5, "main": 10}, "Recruta exploradores e cavalaria."),
        BuildingInfo("garage", "Oficina", 15, {"main": 10, "smith": 10}, "Produz aríetes e catapultas; aldeia ofensiva não passa do nível 5."),
        BuildingInfo("smith", "Ferreiro", 20, {"main": 5, "barracks": 1}, "Pesquisa unidades."),
        BuildingInfo("snob", "Academia", 3, {"market": 10, "main": 20, "smith": 20}, "Forma nobres para conquistar aldeias."),
        BuildingInfo("market", "Mercado", 25, {"main": 3, "storage": 2}, "Troca e envio de recursos; mais níveis, mais mercadores."),
        BuildingInfo("place", "Praça de reunião", 1, {}, "Envia ataques e apoio; mostra tropas em casa."),
        BuildingInfo("statue", "Estátua", 1, {}, "Nomeia o paladino."),
        BuildingInfo("church", "Igreja", 3, {"main": 5, "farm": 5}, "Só em mundos com igreja; tropas fora do raio de fé perdem força."),
        BuildingInfo("watchtower", "Torre de vigia", 20, {}, "Detecta tropas se aproximando (requisitos fora dos docs)."),
        BuildingInfo("wood", "Bosque", 30, {}, "Produz madeira: 30/h no nível 1, 117/h no 10, 530/h no 20."),
        BuildingInfo("stone", "Poço de argila", 30, {}, "Produz argila."),
        BuildingInfo("iron", "Mina de ferro", 30, {}, "Produz ferro; custa mais população que o bosque."),
        BuildingInfo("farm", "Fazenda", 30, {}, "Limite de população: 240 no 1, 1002 no 10, 4904 no 20."),
        BuildingInfo("storage", "Armazém", 30, {}, "Capacidade: 1000 no 1, 6420 no 10, 50675 no 20. Não deixe encher."),
        BuildingInfo("hide", "Esconderijo", 10, {}, "Esconde recursos do saque: 150 no 1, 2000 no 10."),
        BuildingInfo("wall", "Muralha", 20, {"barracks": 1}, "Bônus de defesa: 4% no 1, 44% no 10, 107% no 20."),
    )
}

UNITS: dict[str, UnitInfo] = {
    u.id: u
    for u in (
        UnitInfo("spear", "Lanceiro", (50, 30, 10), 1, 10, (15, 45, 20), 18, 25, "", "Defesa contra cavalaria; saque no início."),
        UnitInfo("sword", "Espadachim", (30, 30, 70), 1, 25, (50, 15, 40), 22, 15, "Ferreiro 1", "Defesa contra infantaria."),
        UnitInfo("axe", "Bárbaro", (60, 30, 40), 1, 40, (10, 5, 10), 18, 10, "Ferreiro 2", "Ataque de infantaria."),
        UnitInfo("archer", "Arqueiro", (100, 30, 60), 1, 15, (50, 40, 5), 18, 10, "Quartel 5, Ferreiro 5", "Defesa."),
        UnitInfo("spy", "Explorador", (50, 50, 20), 2, 0, (2, 1, 2), 9, 0, "Estábulo 1", "Espionagem."),
        UnitInfo("light", "Cavalaria leve", (125, 100, 250), 4, 130, (30, 40, 30), 10, 80, "Estábulo 3", "Unidade ideal de saque."),
        UnitInfo("marcher", "Arqueiro a cavalo", (250, 100, 150), 5, 120, (40, 30, 50), 10, 50, "Estábulo 5", "Ataque."),
        UnitInfo("heavy", "Cavalaria pesada", (200, 150, 600), 6, 150, (200, 80, 180), 11, 50, "Estábulo 10, Ferreiro 15", "Defesa versátil."),
        UnitInfo("ram", "Aríete", (300, 200, 200), 5, 2, (20, 50, 20), 30, 0, "Oficina 1", "Derruba a muralha."),
        UnitInfo("catapult", "Catapulta", (320, 400, 100), 8, 100, (100, 50, 100), 30, 0, "Oficina 2, Ferreiro 12", "Derruba edifícios."),
        UnitInfo("knight", "Paladino", (20, 20, 40), 10, 150, (250, 400, 150), 10, 100, "Estátua", "Um por jogador."),
        UnitInfo("snob", "Nobre", (40000, 50000, 50000), 100, 30, (100, 50, 100), 35, 0, "Academia", "Conquista; envie em ataques separados, sempre com tropas."),
    )
}

BUILDING_BY_LABEL = {info.label.lower(): info.id for info in BUILDINGS.values()}

STRATEGY = """\
Estratégia de base (docs/help):
Economia
- Início: evolua Bosque, Poço de argila e Mina de ferro juntos; o mais baixo sobe primeiro.
- Nunca deixe o Armazém encher: suba-o antes de um recurso passar de 85% da capacidade.
- Suba a Fazenda antes de a população passar de 85%; sem população nada é construído nem recrutado.
- Edifício principal mais alto acelera todas as obras; acompanhe-o com as minas.
- Esconderijo é barato e protege recursos do saque; Muralha (exige Quartel 1) multiplica a defesa.
- Coleta (praça de reunião) rende recursos sem arriscar tropas: desbloqueie os níveis 1 a 4 em ordem.
- Missões e bônus diário dão recursos grátis: conclua, colete e abra os baús assim que possível.
Exército
- Quartel exige Edifício principal 3; lanceiros saqueiam bem no começo (carregam 25).
- Ferreiro exige Edifício principal 5 e Quartel 1; Estábulo exige Quartel 5, Ferreiro 5, Edifício principal 10.
- Cavalaria leve (Estábulo 3) é a melhor unidade de saque: 10 min/campo e carrega 80.
- Defesa: lanceiros contra cavalaria, espadachins contra infantaria; mantenha tropas em casa com ataque chegando.
Saque
- Saque só aldeias bárbaras (sem dono). Nunca ataque jogadores.
- Aldeias bárbaras de pontos altos podem ser ex-jogadores com tropas: prefira as de poucos pontos e perto.
- Grupos pequenos e frequentes rendem mais que um grande; não repita o mesmo alvo logo em seguida.
Nobre
- Academia exige Edifício principal 20, Ferreiro 20 e Mercado 10; Mercado exige Edifício principal 3 e Armazém 2.
- Nobre custa 40000/50000/50000 e 100 de população: Armazém 20 (50675) e Fazenda altos antes.
- Nobre nunca vai sozinho (morre); cada ataque tira 20-35 de lealdade, conquista exige 3-5 ataques seguidos.
- Início tardio num mundo antigo: defesa primeiro (lanceiros e espadachins), nobre depois.
Aldeia final: recursos, Fazenda e Armazém 30; Edifício principal 20; Ferreiro 20; Muralha 20.
Nunca gaste pontos premium.
"""


class GameKnowledge:
    """Lookups over the documented buildings and units."""

    buildings = BUILDINGS
    units = UNITS
    strategy = STRATEGY

    @classmethod
    def building(cls, building: str) -> dict[str, Any] | None:
        info = cls.buildings.get(building) or cls.buildings.get(BUILDING_BY_LABEL.get(building.lower(), ""))
        if info is None:
            return None

        return {
            "id": info.id,
            "label": info.label,
            "max_level": info.max_level,
            "requires": info.requires,
            "role": info.role,
        }

    @classmethod
    def unit(cls, unit: str) -> dict[str, Any] | None:
        info = cls.units.get(unit)
        if info is None:
            return None

        return {
            "id": info.id,
            "label": info.label,
            "cost": {"wood": info.cost[0], "clay": info.cost[1], "iron": info.cost[2]},
            "pop": info.pop,
            "attack": info.attack,
            "defense": {"general": info.defense[0], "cavalry": info.defense[1], "archer": info.defense[2]},
            "minutes_per_field": info.speed,
            "carry": info.carry,
            "requires": info.requires,
            "role": info.role,
        }

    @classmethod
    def missing_requirements(cls, building: str, levels: dict[str, int]) -> dict[str, int]:
        info = cls.buildings.get(building)
        if info is None:
            return {}

        return {req: lvl for req, lvl in info.requires.items() if levels.get(req, 0) < lvl}

    @classmethod
    def goal_building(cls, goal_text: str) -> tuple[str, int] | None:
        """Map a quest goal like "Expanda Bosque ao nível 5." to ("wood", 5)."""
        text = goal_text.lower()

        for label, building in sorted(BUILDING_BY_LABEL.items(), key=lambda kv: -len(kv[0])):
            if label in text:
                digits = [int(tok) for tok in text.replace(".", " ").split() if tok.isdigit()]
                return building, (digits[-1] if digits else 0)

        return None
