"""What the coordinator knows about a village, labelled by how certain it is and how old."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Certainty(StrEnum):
    FACT = "fact"
    ESTIMATE = "estimate"
    HYPOTHESIS = "hypothesis"


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class Insight:
    key: str
    text: str
    certainty: Certainty
    observed_at: datetime
    confidence: float = 1.0
    value: Any = None
    source: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def age_hours(self, at: datetime | None = None) -> float:
        return max(0.0, ((at or now()) - self.observed_at).total_seconds() / 3600)

    def weight(self, half_life_hours: float = 12.0, at: datetime | None = None) -> float:
        """Confidence decayed by age: an old report counts less than a fresh one."""
        return round(self.confidence * 0.5 ** (self.age_hours(at) / half_life_hours), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "text": self.text,
            "certainty": self.certainty.value,
            "observed_at": self.observed_at.isoformat(),
            "age_hours": round(self.age_hours(), 2),
            "confidence": round(self.confidence, 2),
            "weight": self.weight(),
            "source": self.source,
        }
