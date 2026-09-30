"""Taking a barbarian with nobles: scout, clean, then one train of nobles or single nobles until loyalty hits zero."""

import json
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.knowledge import UNITS
from tribal_assistant.core.agents.target_intel import TargetIntel
from tribal_assistant.core.game.world_config import WorldConfig
from tribal_assistant.core.repositories.lessons import LessonRepository
from tribal_assistant.core.repositories.world import WorldRepository

OFFENSIVE = ("axe", "light", "marcher", "heavy", "ram")
ESCORT = ("axe", "light", "marcher", "heavy", "sword", "spear")
FULL_LOYALTY = 100.0


def pop(units: dict[str, int]) -> int:
    return sum(UNITS[u].pop * n for u, n in units.items() if u in UNITS)


@dataclass(frozen=True)
class ConquestStep:
    kind: str
    why: str
    nobles: int = 0
    escort: dict[str, int] = field(default_factory=dict)
    squad: dict[str, int] = field(default_factory=dict)
    loyalty: float = FULL_LOYALTY


class Loyalty:
    @staticmethod
    def now(state: dict[str, Any], per_hour: float, at: datetime | None = None) -> float:
        """Estimated loyalty of the target: the last estimate plus what it regained since."""
        if "loyalty" not in state or not state.get("at"):
            return FULL_LOYALTY

        stamp = datetime.fromisoformat(str(state["at"]))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)

        hours = max(0.0, ((at or datetime.now(UTC)) - stamp).total_seconds() / 3600)
        return min(FULL_LOYALTY, float(state["loyalty"]) + per_hour * hours)

    @staticmethod
    def after(loyalty: float, nobles: int, hit: int) -> float:
        return max(0.0, loyalty - nobles * hit)

    @staticmethod
    def nobles_needed(loyalty: float, hit: int) -> int:
        return max(1, math.ceil(loyalty / max(1, hit)))


class Escort:
    @staticmethod
    def per_wave(home: dict[str, int], waves: int, min_pop: int) -> dict[str, int] | None:
        """Troops that go with each noble, offensive first, at least `min_pop` of population per wave."""
        if waves <= 0:
            return None

        escort: dict[str, int] = {}
        for unit in ESCORT:
            share = home.get(unit, 0) // waves
            if share <= 0:
                continue

            wanted = math.ceil(max(0, min_pop - pop(escort)) / UNITS[unit].pop)
            take = min(share, wanted)
            if take > 0:
                escort[unit] = take

            if pop(escort) >= min_pop:
                return escort

        return None

    @staticmethod
    def cleanup(home: dict[str, int], share: float, min_pop: int, keep: dict[str, int] | None = None) -> dict[str, int] | None:
        """The offensive troops that clear the target before the nobles."""
        keep = keep or {}
        squad = {u: int(max(0, home.get(u, 0) - keep.get(u, 0)) * share) for u in OFFENSIVE}
        squad = {u: n for u, n in squad.items() if n > 0}
        return squad if pop(squad) >= min_pop else None


class ConquestPlanner:
    """Next step against one barbarian from the scouting, the last reports and the loyalty estimate."""

    @staticmethod
    def step(intel: dict[str, Any], state: dict[str, Any], home: dict[str, int], per_hour: float, knobs: Knobs, travelling: bool = False) -> ConquestStep:
        nobles = home.get("snob", 0)
        loyalty = Loyalty.now(state, per_hour)
        if nobles <= 0:
            return ConquestStep("wait", "sem nobre em casa", loyalty=loyalty)

        if travelling:
            return ConquestStep("wait", "ataque já a caminho do alvo", loyalty=loyalty)

        scouted = TargetIntel.age_hours(intel, "scouted_at")
        if scouted is None or scouted > knobs.get("conquest.scout_hours"):
            return ConquestStep("scout", "alvo sem espionagem recente", loyalty=loyalty)

        cleaned = TargetIntel.age_hours(intel, "looted_at")
        clear = intel.get("last_result") == "green" and not intel.get("defenders_left")
        if cleaned is None or cleaned > knobs.get("conquest.clean_hours") or not clear:
            squad = Escort.cleanup(home, knobs.get("conquest.cleanup_share"), knobs.int("conquest.cleanup_pop"))
            if squad is None:
                return ConquestStep("wait", "tropa ofensiva insuficiente para a limpeza", loyalty=loyalty)

            return ConquestStep("cleanup", "limpar a bárbara antes do nobre", squad=squad, loyalty=loyalty)

        last = TargetIntel.age_hours(state, "noble_at")
        if last is not None and last * 60 < knobs.int("conquest.noble_gap_minutes"):
            return ConquestStep("wait", "nobre enviado há pouco", loyalty=loyalty)

        needed = Loyalty.nobles_needed(loyalty, knobs.int("conquest.loyalty_hit"))
        waves = min(nobles, needed, knobs.int("conquest.train_max"))
        escort = None
        while waves > 0:
            escort = Escort.per_wave({u: n for u, n in home.items() if u != "snob"}, waves, knobs.int("conquest.escort_pop"))
            if escort is not None:
                break
            waves -= 1

        if escort is None:
            return ConquestStep("wait", "escolta insuficiente para o nobre", loyalty=loyalty)

        why = f"lealdade ~{loyalty:.0f}: {waves} nobre(s) " + ("no mesmo trem" if waves > 1 else "um por vez até zerar")
        return ConquestStep("noble", why, nobles=waves, escort=escort, loyalty=loyalty)


class ConquestBook:
    """What we know about each conquest in progress, kept as a lesson per target."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = LessonRepository(session)
        self.world = WorldRepository(session)

    async def per_hour(self) -> float:
        config = WorldConfig.from_settings(await self.world.setting("config"), await self.world.setting("units"))
        return config.loyalty_per_hour

    async def state(self, coords: str) -> dict[str, Any]:
        row = await self.repo.get(f"conquest:{coords}")
        return json.loads(row.data or "{}") if row else {}

    async def sent(self, coords: str, origin: int, nobles: int, hit: int) -> dict[str, Any]:
        now = datetime.now(UTC)
        loyalty = Loyalty.after(Loyalty.now(await self.state(coords), await self.per_hour(), now), nobles, hit)
        data = {"loyalty": loyalty, "at": now.isoformat(), "noble_at": now.isoformat(), "origin": origin, "nobles": nobles}
        await self.repo.observe(f"conquest:{coords}", "conquest", f"conquista {coords}", f"{nobles} nobre(s), lealdade estimada {loyalty:.0f}", data)
        return data
