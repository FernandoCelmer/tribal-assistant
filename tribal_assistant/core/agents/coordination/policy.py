"""Limits the coordinator decides per village role instead of fixed settings."""

from dataclasses import dataclass

BUILD_SLOTS = 2


@dataclass(frozen=True)
class Policy:
    role: str = "growth"
    resource_reserve: float = 0.1
    recruit_budget: float = 0.3
    max_attacks_per_hour: int = 12
    attack_radius: int = 12
    retarget_minutes: int = 30
    build_queue_slots: int = BUILD_SLOTS

    @classmethod
    def for_role(cls, role: str) -> "Policy":
        return POLICIES.get(role, POLICIES["growth"])

    def describe(self) -> str:
        return (
            f"reserva {self.resource_reserve:.0%}, recrutamento até {self.recruit_budget:.0%} da sobra, "
            f"até {self.max_attacks_per_hour} ataques/h num raio de {self.attack_radius} campos, "
            f"mesmo alvo a cada {self.retarget_minutes} min"
        )


POLICIES = {
    "growth": Policy("growth", 0.1, 0.3, 12, 12, 30),
    "expansion": Policy("expansion", 0.1, 0.3, 12, 12, 30),
    "defense": Policy("defense", 0.1, 0.8, 4, 8, 60),
    "support": Policy("support", 0.1, 0.7, 6, 10, 45),
    "offensive": Policy("offensive", 0.05, 0.7, 30, 15, 20),
    "emergency": Policy("emergency", 0.0, 0.9, 0, 0, 999),
}
