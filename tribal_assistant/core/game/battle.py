"""Battle simulator with the game formula: attack split by type, wall bonus, winner losses by the 1.5 power."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from tribal_assistant.core.agents.knowledge import UNITS

INFANTRY = "infantry"
CAVALRY = "cavalry"
ARCHER = "archer"

UNIT_TYPE = {
    "spear": INFANTRY,
    "sword": INFANTRY,
    "axe": INFANTRY,
    "ram": INFANTRY,
    "catapult": INFANTRY,
    "snob": INFANTRY,
    "militia": INFANTRY,
    "light": CAVALRY,
    "heavy": CAVALRY,
    "knight": CAVALRY,
    "archer": ARCHER,
    "marcher": ARCHER,
}
DEFENSE_INDEX = {INFANTRY: 0, CAVALRY: 1, ARCHER: 2}
WALL_FACTOR = 1.037
BASE_DEFENSE = 20
WALL_DEFENSE = 50
LOSS_POWER = 1.5


@dataclass(frozen=True)
class BattleResult:
    attack: float
    defense: float
    attacker_wins: bool
    attacker_loss_ratio: float
    defender_loss_ratio: float
    attacker_losses: dict[str, int] = field(default_factory=dict)
    defender_losses: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "attack": round(self.attack),
            "defense": round(self.defense),
            "attacker_wins": self.attacker_wins,
            "attacker_loss_ratio": round(self.attacker_loss_ratio, 3),
            "defender_loss_ratio": round(self.defender_loss_ratio, 3),
            "attacker_losses": self.attacker_losses,
            "defender_losses": self.defender_losses,
        }


class BattleSimulator:
    def __init__(self, units: Mapping = UNITS) -> None:
        self.units = units

    def attack_by_type(self, army: Mapping[str, int]) -> dict[str, float]:
        power = {INFANTRY: 0.0, CAVALRY: 0.0, ARCHER: 0.0}
        for unit, count in army.items():
            info = self.units.get(unit)
            if info is None or unit == "spy" or count <= 0:
                continue

            power[UNIT_TYPE.get(unit, INFANTRY)] += info.attack * count

        return power

    def defense_against(self, army: Mapping[str, int], shares: Mapping[str, float]) -> float:
        total = 0.0
        for unit, count in army.items():
            info = self.units.get(unit)
            if info is None or count <= 0:
                continue

            total += count * sum(info.defense[DEFENSE_INDEX[kind]] * share for kind, share in shares.items())

        return total

    def simulate(
        self,
        attacker: Mapping[str, int],
        defender: Mapping[str, int],
        wall: int = 0,
        *,
        luck: float = 0.0,
        morale: float = 1.0,
    ) -> BattleResult:
        power = self.attack_by_type(attacker)
        attack = sum(power.values()) * (1 + luck) * morale
        raw = sum(power.values())
        shares = {kind: value / raw for kind, value in power.items()} if raw else {INFANTRY: 1.0}
        wall = max(0, int(wall))
        defense = self.defense_against(defender, shares) * WALL_FACTOR**wall + BASE_DEFENSE + WALL_DEFENSE * wall

        if attack <= 0:
            fighters = {u: n for u, n in attacker.items() if u != "spy"}
            return BattleResult(0.0, defense, False, 1.0 if any(n > 0 for n in fighters.values()) else 0.0, 0.0, self._losses(fighters, 1.0), {})

        wins = attack > defense
        winner_ratio = (min(attack, defense) / max(attack, defense)) ** LOSS_POWER
        attacker_ratio = winner_ratio if wins else 1.0
        defender_ratio = 1.0 if wins else winner_ratio

        return BattleResult(
            attack,
            defense,
            wins,
            attacker_ratio,
            defender_ratio,
            self._losses(attacker, attacker_ratio),
            self._losses(defender, defender_ratio),
        )

    @staticmethod
    def _losses(army: Mapping[str, int], ratio: float) -> dict[str, int]:
        return {unit: min(count, round(count * ratio)) for unit, count in army.items() if count > 0}


def simulate_battle(
    attacker_units: Mapping[str, int],
    defender_units: Mapping[str, int],
    wall: int = 0,
    *,
    luck: float = 0.0,
    morale: float = 1.0,
) -> BattleResult:
    return BattleSimulator().simulate(attacker_units, defender_units, wall, luck=luck, morale=morale)
