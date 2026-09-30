"""A comparable action proposal: what, why, cost, deadline, confidence and the factors of its priority."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class Horizon(StrEnum):
    IMMEDIATE = "immediate"
    TACTICAL = "tactical"
    STRATEGIC = "strategic"


@dataclass
class Factors:
    urgency: float = 0.0
    impact: float = 0.0
    risk_avoided: float = 0.0
    opportunity: float = 0.0
    opportunity_cost: float = 0.0
    uncertainty: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: round(v, 2) for k, v in self.__dict__.items()}


@dataclass
class Proposal:
    source: str
    action: str
    arguments: dict[str, Any]
    reason: str
    expected_benefit: str = ""
    cost: dict[str, int] = field(default_factory=dict)
    troops: dict[str, int] = field(default_factory=dict)
    factors: Factors = field(default_factory=Factors)
    horizon: Horizon = Horizon.TACTICAL
    deadline: datetime | None = None
    confidence: float = 1.0
    dependencies: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    purpose: str = ""
    key: str = ""
    priority: float = 0.0
    bonus: float = 1.0
    explored: bool = False
    display: str = ""

    def __post_init__(self) -> None:
        self.factors.uncertainty = max(self.factors.uncertainty, 1.0 - self.confidence)
        self.key = self.key or f"{self.action}:{self.label()}"

    def label(self) -> str:
        args = self.arguments
        return str(args.get("building") or args.get("unit") or args.get("to_village_id") or args.get("target") or args.get("option_id") or args.get("key") or args.get("skill_id") or args.get("regimen") or args.get("quest_id") or args.get("mail_id") or args.get("to") or args.get("name") or args.get("buddy_id") or args.get("thread_id") or args.get("ally_id") or args.get("invite_id") or args.get("mentor_id") or "")

    def title(self) -> str:
        if self.display:
            return self.display
        label = self.label()
        return f"{self.action} {label}".strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "source": self.source,
            "action": self.action,
            "title": self.title(),
            "arguments": {k: v for k, v in self.arguments.items() if k != "reason"},
            "reason": self.reason,
            "expected_benefit": self.expected_benefit,
            "priority": round(self.priority, 1),
            "bonus": round(self.bonus, 2),
            "exploration": self.explored,
            "cost": self.cost,
            "troops": self.troops,
            "factors": self.factors.to_dict(),
            "horizon": self.horizon.value,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "confidence": round(self.confidence, 2),
            "dependencies": self.dependencies,
            "risks": self.risks,
            "purpose": self.purpose,
        }
