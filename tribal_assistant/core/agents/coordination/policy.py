"""Limits the coordinator decides per village role, read from the self-tuning knobs."""

from dataclasses import dataclass, field

from tribal_assistant.core.agents.knob_catalog import POLICY_FIELDS, ROLE_LIMITS
from tribal_assistant.core.agents.knobs import Knobs

BUILD_SLOTS = 2
EMERGENCY_RETARGET_MINUTES = 999


@dataclass(frozen=True)
class Policy:
    role: str = "growth"
    resource_reserve: float = 0.1
    recruit_budget: float = 0.3
    max_attacks_per_hour: int = 12
    attack_radius: int = 12
    retarget_minutes: int = 30
    build_queue_slots: int = BUILD_SLOTS
    knobs: Knobs = field(default_factory=Knobs, compare=False, hash=False, repr=False)

    @classmethod
    def for_role(cls, role: str, knobs: Knobs | None = None) -> "Policy":
        knobs = knobs or Knobs()
        if role == "emergency":
            return cls("emergency", 0.0, knobs.get("policy.emergency.recruit_budget"), 0, 0, EMERGENCY_RETARGET_MINUTES, knobs=knobs)

        role = role if role in ROLE_LIMITS else "growth"
        reserve, budget, attacks, radius, retarget = (f"policy.{role}.{name}" for name in POLICY_FIELDS)
        return cls(role, knobs.get(reserve), knobs.get(budget), knobs.int(attacks), knobs.int(radius), knobs.int(retarget), knobs=knobs)

    def describe(self) -> str:
        return (
            f"reserva {self.resource_reserve:.0%}, recrutamento até {self.recruit_budget:.0%} da sobra, "
            f"até {self.max_attacks_per_hour} ataques/h num raio de {self.attack_radius} campos, "
            f"mesmo alvo a cada {self.retarget_minutes} min"
        )
