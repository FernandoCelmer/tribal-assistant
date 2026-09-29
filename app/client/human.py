"""Human-like pacing and input: delays, mouse paths, reading pauses."""

import asyncio
import random
from datetime import datetime

from playwright.async_api import Locator, Page

from app.core.config import settings


async def human_delay(min_ms: int | None = None, max_ms: int | None = None) -> None:
    lo = min_ms or settings.min_delay_ms
    hi = max_ms or settings.max_delay_ms
    delay = random.uniform(lo, hi)
    if random.random() < 0.08:
        delay += random.uniform(2000, 7000)
    await asyncio.sleep(delay / 1000)


async def wander_mouse(page: Page, moves: int | None = None) -> None:
    viewport = page.viewport_size or {"width": 1280, "height": 720}
    for _ in range(moves if moves is not None else random.randint(1, 3)):
        await page.mouse.move(
            random.uniform(40, viewport["width"] - 40),
            random.uniform(80, viewport["height"] - 40),
            steps=random.randint(8, 25),
        )
        await asyncio.sleep(random.uniform(0.05, 0.3))


async def reading_pause(page: Page) -> None:
    await wander_mouse(page)
    if random.random() < 0.5:
        for _ in range(random.randint(1, 3)):
            await page.mouse.wheel(0, random.randint(120, 480))
            await asyncio.sleep(random.uniform(0.3, 1.2))
        if random.random() < 0.6:
            await page.mouse.wheel(0, -random.randint(200, 900))
    await human_delay()


async def human_click(page: Page, target: Locator) -> None:
    await target.scroll_into_view_if_needed()
    box = await target.bounding_box()
    if box is None:
        await target.click()
        return
    x = box["x"] + box["width"] * random.uniform(0.25, 0.75)
    y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
    await page.mouse.move(x, y, steps=random.randint(10, 30))
    await asyncio.sleep(random.uniform(0.08, 0.35))
    await page.mouse.click(x, y, delay=random.randint(40, 140))


def in_quiet_hours(now: datetime | None = None) -> bool:
    """`QUIET_HOURS=1-7` pauses scheduled syncs from 01:00 to 06:59 local time."""
    if not settings.quiet_hours:
        return False
    start, end = (int(part) for part in settings.quiet_hours.split("-", 1))
    hour = (now or datetime.now()).hour
    return start <= hour < end if start <= end else hour >= start or hour < end
