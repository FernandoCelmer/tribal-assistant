"""Farm runner — turns FarmTarget rows into browser-driven attacks.

This is a stub: real dispatch will use the in-game Farm Assistant screen.
Kept behind a stable interface so the service layer doesn't change when
the automation matures.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from loguru import logger

from tribal_assistant.models.farm_target import FarmTarget


@dataclass
class FarmDispatchResult:
    dispatched: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    persisted_loots: dict[str, int] = field(default_factory=dict)


class FarmRunner:
    async def dispatch(self, targets: Sequence[FarmTarget]) -> FarmDispatchResult:
        result = FarmDispatchResult()

        if not targets:
            logger.info("No farm targets to dispatch")
            return result

        for target in targets:
            logger.info("(stub) would farm {}", target.coords)
            result.skipped += 1

        return result
