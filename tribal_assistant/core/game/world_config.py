"""World rules read from the stored `get_config` and `get_unit_info` settings."""

from dataclasses import dataclass, field
from typing import Any

NOBLE_UNIT_COST = {"wood": 40000, "clay": 50000, "iron": 50000}
DEFAULT_COIN = {"wood": 28000, "clay": 30000, "iron": 25000}
NOBLE_SYSTEMS = {0: "packages", 1: "coins"}
FARM_BONUS = 4


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    return value if isinstance(value, dict) else {}


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class NightBonus:
    active: bool = False
    start_hour: int = 0
    end_hour: int = 0
    defense_factor: float = 1.0


@dataclass(frozen=True)
class WorldConfig:
    speed: float = 1.0
    unit_speed: float = 1.0
    noble_system: str = "coins"
    coin_cost: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_COIN))
    noble_max_distance: int = 0
    loyalty_rise: float = 1.0
    barbarian_rise: float = 0.0
    barbarian_max_points: int = 0
    militia: bool = False
    watchtower: bool = False
    knight: bool = False
    archer: bool = False
    church: bool = False
    night: NightBonus = field(default_factory=NightBonus)
    protection_days: float = 0.0

    @classmethod
    def from_settings(cls, config: dict[str, Any] | None, units: dict[str, Any] | None = None) -> "WorldConfig":
        config = config or {}
        units = units or {}
        game = _section(config, "game")
        snob = _section(config, "snob")
        night = _section(config, "night")
        newbie = _section(config, "newbie")

        return cls(
            speed=_number(config.get("speed"), 1.0),
            unit_speed=_number(config.get("unit_speed"), 1.0),
            noble_system=NOBLE_SYSTEMS.get(int(_number(snob.get("gold"), 1)), "levels"),
            coin_cost={
                "wood": int(_number(snob.get("coin_wood"), DEFAULT_COIN["wood"])),
                "clay": int(_number(snob.get("coin_stone"), DEFAULT_COIN["clay"])),
                "iron": int(_number(snob.get("coin_iron"), DEFAULT_COIN["iron"])),
            },
            noble_max_distance=int(_number(snob.get("max_dist"), 0)),
            loyalty_rise=_number(snob.get("rise"), 1.0),
            barbarian_rise=_number(game.get("barbarian_rise"), 0.0),
            barbarian_max_points=int(_number(game.get("barbarian_max_points"), 0)),
            militia="militia" in units,
            watchtower=bool(_number(game.get("watchtower"), 0)),
            knight=bool(_number(game.get("knight"), 0)),
            archer=bool(_number(game.get("archer"), 0)),
            church=bool(_number(game.get("church"), 0)),
            night=NightBonus(
                active=bool(_number(night.get("active"), 0)),
                start_hour=int(_number(night.get("start_hour"), 0)),
                end_hour=int(_number(night.get("end_hour"), 0)),
                defense_factor=_number(night.get("def_factor"), 1.0),
            ),
            protection_days=_number(newbie.get("days"), 0.0),
        )

    @property
    def loyalty_per_hour(self) -> float:
        return self.loyalty_rise * self.speed

    def noble_cost(self, ordinal: int) -> dict[str, int]:
        """Resources for the n-th noble: the unit plus n coins or n packages; the levels system adds nothing."""
        ordinal = max(1, ordinal)
        extra = ordinal if self.noble_system in ("coins", "packages") else 0
        return {r: NOBLE_UNIT_COST[r] + extra * self.coin_cost[r] for r in NOBLE_UNIT_COST}

    def summary(self) -> str:
        systems = {"coins": "moedas", "packages": "armazenamento", "levels": "níveis"}
        night = f"{self.night.start_hour}h-{self.night.end_hour}h" if self.night.active else "desligado"
        return (
            f"velocidade {self.speed:g}, unidades {self.unit_speed:g}, nobre por {systems[self.noble_system]}, "
            f"lealdade +{self.loyalty_per_hour:g}/h, bárbaras crescem {self.barbarian_rise:g}, "
            f"milícia {'sim' if self.militia else 'não'}, torre {'sim' if self.watchtower else 'não'}, "
            f"bônus noturno {night}, proteção {self.protection_days:g} dias"
        )
