"""Game facts taken from docs/help (pt-BR Tribal Wars help pages).

Only what the docs state; unknown prerequisites are left empty and the game's
own "can build" answer stays the final word.
"""

from dataclasses import dataclass, field
from pathlib import Path
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
Estratégia de base (docs/help e tutoriais do fórum; mundo velocidade 2, unidades 0,5):
Início (proteção de iniciante)
- Estátua 1 logo depois do Quartel 1: o paladino saqueia desde o primeiro dia.
- Missões dão recursos: faça Muralha 1 (devolve 300 de cada) e Esconderijo 3 (dá 100); por missão, nunca acima do 3.
- Nunca ative a milícia, nem por missão: ela para as minas.
- Minas: madeira sempre a mais alta; ferro 3 níveis abaixo de madeira e argila até existir Estábulo.
- Lanceiros sem parar até 40: a missão dos 40 dá 900/500/300 e 10 dias de assistente de saque.
- Portão da cavalaria leve: Edifício principal 10 (não passe disso antes do Estábulo 3), Quartel 5, Ferreiro 5, Estábulo 3, Armazém 6-7 para caber os custos.
- Nunca deixe o Armazém encher; suba a Fazenda antes de a população passar de 85%.
Fim da proteção (preparar nas 72h finais)
- Muralha 8, cerca de 80 lanceiros e 80 espadachins em casa; machados só ~12h antes do fim.
- Depois da proteção: a cada 3 níveis de EP, 2 de Quartel e 2 de Estábulo.
Saque
- Só aldeias bárbaras; nunca ataque jogadores. Espione antes de saquear quem não conhece.
- Grupos seguros: 5+ lanceiros com o paladino, ou 4 lanceiros + 3 espadachins.
- Cavalaria leve sem perdas por muralha da bárbara: 0 → 1 + 1 espião, 1 → 2, 2 → 8, 3 → 22, 4 → 46, 5 → 85.
- Suba a escala por bárbara conforme o saque volta cheio: 2 → 5 → 7 cavalarias leves.
- Bárbara com academia, estátua ou praça é ex-jogador: espione e mande mais.
- Com ataque chegando, esquive: tire as tropas de casa até o impacto passar e volte a saquear.
Coleta
- Lanceiro é a unidade da coleta (25 de carga por 1 de população); divida para as coletas terminarem juntas.
Nobre
- Academia exige Edifício principal 20, Ferreiro 20 e Mercado 10; nobre só com Fazenda 24 e exército de verdade.
- Nobre custa 40000/50000/50000 e 100 de população, mais n moedas (ou n pacotes de 28000/30000/25000) para o n-ésimo nobre.
- Primeiro alvo: bárbara próxima já espionada (melhor se tiver bônus de fazenda) ou a bárbara grande mais perto.
- Nobre nunca vai sozinho; cada ataque tira 20-35 de lealdade. Trem de 4 conquista em ~85%, 5 em 100%.
- Lealdade volta ~2 por hora na velocidade 2: não espace os nobres.
Aldeia final: recursos, Fazenda e Armazém 30; Edifício principal 20; Ferreiro 20; Muralha 20.
Nunca gaste pontos premium.
Guias completos: lookup_knowledge kind=guide id=inicio (primeiros dias), coleta, avancado (várias aldeias, tribo), nobre (conquista) ou tribo.
"""

GUIDES = {
    "inicio": "Primeiros dias: economia de saque, ordem de construção, missões, coleta, tropas e rotina.",
    "avancado": "Fase avançada: especialização de aldeias, mercado, ataques sincronizados, defesa e tribo.",
    "nobre": "Conquista: academia, espionagem, limpeza, nobres sincronizados e defesa da aldeia nova.",
    "tribo": "Tribos: para que servem, como escolher, riscos e como entram no planejamento.",
    "coleta": "Coleta: custos, quanto rende cada nível, como dividir as tropas e por que recrutar lanceiros.",
}
GUIDES_DIR = Path(__file__).parent / "guides"


class GameKnowledge:
    """Lookups over the documented buildings and units."""

    buildings = BUILDINGS
    units = UNITS
    strategy = STRATEGY
    guides = GUIDES

    @classmethod
    def guide(cls, name: str) -> str | None:
        if name not in GUIDES:
            return None

        return (GUIDES_DIR / f"{name}.md").read_text(encoding="utf-8")

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
