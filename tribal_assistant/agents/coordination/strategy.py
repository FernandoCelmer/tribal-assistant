"""Village roles chosen by the coordinator and the weights each role gives to the priority factors."""

from dataclasses import dataclass
from enum import StrEnum

from tribal_assistant.agents.coordination.proposal import Factors


class Role(StrEnum):
    GROWTH = "growth"
    DEFENSE = "defense"
    OFFENSIVE = "offensive"
    SUPPORT = "support"
    EXPANSION = "expansion"
    EMERGENCY = "emergency"


LABELS = {
    Role.GROWTH: "Crescimento",
    Role.DEFENSE: "Defesa",
    Role.OFFENSIVE: "Ofensiva",
    Role.SUPPORT: "Apoio",
    Role.EXPANSION: "Expansão",
    Role.EMERGENCY: "Emergência",
}

GOALS = {
    Role.GROWTH: "aumentar a produção sem saturar armazém nem fazenda",
    Role.DEFENSE: "preservar tropas e recursos para resistir a ameaças",
    Role.OFFENSIVE: "formar exército e manter saques constantes",
    Role.SUPPORT: "produzir defesa para proteger outras aldeias",
    Role.EXPANSION: "reunir economia, academia e nobres para outra aldeia",
    Role.EMERGENCY: "segurar o ataque que está chegando",
}


@dataclass(frozen=True)
class Weights:
    urgency: float
    impact: float
    risk_avoided: float
    opportunity: float
    opportunity_cost: float
    uncertainty: float

    def score(self, f: Factors) -> float:
        raw = (
            self.urgency * f.urgency
            + self.impact * f.impact
            + self.risk_avoided * f.risk_avoided
            + self.opportunity * f.opportunity
            - self.opportunity_cost * f.opportunity_cost
            - self.uncertainty * f.uncertainty
        )
        return round(max(0.0, min(1.0, raw)) * 100, 1)


WEIGHTS = {
    Role.GROWTH: Weights(0.25, 0.4, 0.15, 0.2, 0.1, 0.1),
    Role.DEFENSE: Weights(0.3, 0.2, 0.35, 0.1, 0.1, 0.15),
    Role.OFFENSIVE: Weights(0.25, 0.3, 0.1, 0.35, 0.1, 0.15),
    Role.SUPPORT: Weights(0.25, 0.3, 0.3, 0.1, 0.1, 0.1),
    Role.EXPANSION: Weights(0.2, 0.45, 0.15, 0.15, 0.1, 0.1),
    Role.EMERGENCY: Weights(0.45, 0.05, 0.45, 0.05, 0.05, 0.1),
}
