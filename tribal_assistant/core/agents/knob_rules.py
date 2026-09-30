"""What the tuner measures and the rules that turn a measurement into one step up or down."""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Metrics:
    """Shares of coordination rounds in the window where each situation happened."""

    rounds: int = 0
    idle_queue: float = 0.0
    recruit_starved: float = 0.0
    stock_empty: float = 0.0
    storage_full: float = 0.0
    pop_locked: float = 0.0
    scavenge_idle: float = 0.0
    raids_vetoed: float = 0.0
    raids_lost: float = 0.0
    raids_capped: float = 0.0
    no_targets: float = 0.0
    threatened: float = 0.0
    iron_short: float = 0.0
    actions_capped: float = 0.0
    dodge_stuck: float = 0.0
    nobles_failed: float = 0.0
    shipments_failed: float = 0.0
    nothing_to_do: dict[str, float] = field(default_factory=dict)


Rule = Callable[[Metrics], tuple[int, str] | None]


@dataclass(frozen=True)
class KnobSpec:
    default: float
    description: str
    rule: Rule | None = None
    share: bool = False
    integer: bool = False


def more_when(metric: str, above: float, why: str) -> Rule:
    return lambda m: (+1, f"{why} ({getattr(m, metric):.0%})") if getattr(m, metric) > above else None


def less_when(metric: str, above: float, why: str) -> Rule:
    return lambda m: (-1, f"{why} ({getattr(m, metric):.0%})") if getattr(m, metric) > above else None


def either(*rules: Rule) -> Rule:
    def rule(m: Metrics) -> tuple[int, str] | None:
        for candidate in rules:
            result = candidate(m)
            if result:
                return result
        return None

    return rule


def cooldown(action: str) -> Rule:
    """Wait longer between checks that keep finding nothing, shorter when they keep finding work."""

    def rule(m: Metrics) -> tuple[int, str] | None:
        empty = m.nothing_to_do.get(action)
        if empty is None:
            return None
        if empty > 0.7:
            return +1, f"{action} sem nada a fazer em {empty:.0%} das tentativas"
        if empty < 0.2:
            return -1, f"{action} encontrou trabalho em {1 - empty:.0%} das tentativas"
        return None

    return rule


def cooldowns(*actions: str) -> Rule:
    return either(*(cooldown(action) for action in actions))


def settle(metric: str, below: float, why: str) -> Rule:
    """Once the problem is gone, walk back towards the default one step at a time."""
    return lambda m: (0, f"{why} resolvido ({getattr(m, metric):.0%}): volta ao padrão") if getattr(m, metric) < below else None
