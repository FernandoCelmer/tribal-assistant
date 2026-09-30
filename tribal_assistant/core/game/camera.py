"""Pictures of the village illustration on the overview screen, taken while the sync is already there."""

from dataclasses import dataclass, field

from loguru import logger
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page

VISUAL_SELECTORS = ("#show_summary .visual", ".village-overview .visual", "#content_value .visual")


@dataclass(frozen=True)
class Shot:
    image: bytes
    width: int
    height: int


@dataclass
class VillageCamera:
    """Keeps one picture per village for the sync, shrinking the JPEG quality until it fits the size limit."""

    quality: int = 70
    max_bytes: int = 150 * 1024
    min_quality: int = 20
    quality_step: int = 15
    timeout_ms: int = 5000
    shots: dict[str, Shot] = field(default_factory=dict)

    async def capture(self, page: Page, village_id: str) -> Shot | None:
        try:
            shot = await self.take(page)
        except PlaywrightError as exc:
            logger.debug("Não foi possível fotografar a aldeia {}: {}", village_id, exc)
            return None

        if shot is not None:
            self.shots[village_id] = shot
        return shot

    async def take(self, page: Page) -> Shot | None:
        for selector in VISUAL_SELECTORS:
            element = page.locator(selector).first
            if await element.count() and await element.is_visible():
                box = await element.bounding_box()
                if not box or box["width"] < 1 or box["height"] < 1:
                    continue
                return Shot(await self.encode(element), round(box["width"]), round(box["height"]))
        return None

    async def encode(self, element: Locator) -> bytes:
        quality = max(self.min_quality, min(100, self.quality))
        image = await element.screenshot(type="jpeg", quality=quality, timeout=self.timeout_ms, animations="disabled")
        while len(image) > self.max_bytes and quality > self.min_quality:
            quality = max(self.min_quality, quality - self.quality_step)
            image = await element.screenshot(type="jpeg", quality=quality, timeout=self.timeout_ms, animations="disabled")
        return image
