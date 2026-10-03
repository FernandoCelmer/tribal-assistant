"""What the tuner measures and the rules that turn a measurement into one step up or down."""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Metrics:
    """Shares of coordination rounds in the window where each situation happened."""

    rounds: int = 0
    idle_queue: float = 0.0
    idle_recruiting: float = 0.0
    army_stalled: float = 0.0
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
    mail_capped: float = 0.0
    contacts_unanswered: float = 0.0
    builds_done: float = 0.0
    farm_full: float = 0.0
    farm_partial: float = 0.0
    social_idle: float = 0.0
    repetition: float = 0.0
    explored: int = 0
    explore_gap: float = 0.0
    yields: dict[str, float] = field(default_factory=dict)
    factor_gaps: dict[str, float] = field(default_factory=dict)
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

    rule.steady_up = any(getattr(candidate, "steady_up", False) for candidate in rules)
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

    rule.steady_up = True
    return rule


def cooldowns(*actions: str) -> Rule:
    return either(*(cooldown(action) for action in actions))


def settle(metric: str, below: float, why: str) -> Rule:
    """Once the problem is gone, walk back towards the default one step at a time."""
    return lambda m: (0, f"{why} resolvido ({getattr(m, metric):.0%}): volta ao padrão") if getattr(m, metric) < below else None


def less_when_many(metric: str, above: float, why: str) -> Rule:
    """Like less_when for a count instead of a share."""
    return lambda m: (-1, f"{why} ({getattr(m, metric):g})") if getattr(m, metric) > above else None


def settle_when_few(metric: str, below: float, why: str) -> Rule:
    """Like settle for a count instead of a share."""
    return lambda m: (0, f"{why}: só {getattr(m, metric):g}, volta ao padrão") if getattr(m, metric) < below else None


def specialist_yield(source: str, margin: float) -> Rule:
    """Bonus of a specialist: up when its actions yield more than the average specialist, down when less."""

    def rule(m: Metrics) -> tuple[int, str] | None:
        value = m.yields.get(source)
        if value is None or len(m.yields) < 2:
            return 0, f"{source} sem resultado medido: volta ao padrão"
        mean = sum(m.yields.values()) / len(m.yields)
        if value - mean > margin:
            return +1, f"{source} rende {value:+.2f} contra média {mean:+.2f}"
        if mean - value > margin:
            return -1, f"{source} rende {value:+.2f} contra média {mean:+.2f}"
        return 0, f"{source} rende na média ({value:+.2f}): volta ao padrão"

    return rule


def factor_yield(role: str, factor: str, penalty: bool, margin: float) -> Rule:
    """Weight of a factor in a role: up when proposals strong in it yielded more, down when they yielded less."""

    def rule(m: Metrics) -> tuple[int, str] | None:
        gap = m.factor_gaps.get(f"{role}.{factor}")
        if gap is None:
            return 0, f"{factor} no papel {role} sem medição: volta ao padrão"
        signed = -gap if penalty else gap
        if signed > margin:
            return +1, f"propostas com {factor} alto rendem {gap:+.2f} no papel {role}"
        if signed < -margin:
            return -1, f"propostas com {factor} alto rendem {gap:+.2f} no papel {role}"
        return 0, f"{factor} no papel {role} sem diferença ({gap:+.2f}): volta ao padrão"

    return rule


def exploration(repeat_above: float, worse_below: float, samples: int) -> Rule:
    """More exploration when rounds repeat themselves, less when explored actions yield worse than the usual ones."""

    def rule(m: Metrics) -> tuple[int, str] | None:
        if m.explored >= samples and m.explore_gap < worse_below:
            return -1, f"explorações rendem {m.explore_gap:+.2f} abaixo das escolhas normais"
        if m.repetition > repeat_above:
            return +1, f"rodadas repetindo as mesmas ações ({m.repetition:.0%})"
        if m.explored >= samples and m.explore_gap > -worse_below:
            return +1, f"explorações rendem {m.explore_gap:+.2f} acima das escolhas normais"
        return 0, f"rodadas variadas ({m.repetition:.0%} repetidas): volta ao padrão"

    return rule
