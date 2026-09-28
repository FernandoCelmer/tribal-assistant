"""Human-like delays."""

import asyncio
import random

from app.core.config import settings


async def human_delay(min_ms: int | None = None, max_ms: int | None = None) -> None:
    lo = min_ms or settings.min_delay_ms
    hi = max_ms or settings.max_delay_ms
    await asyncio.sleep(random.uniform(lo, hi) / 1000)
