from pathlib import Path

import pytest
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from tribal_assistant.core.game.camera import VillageCamera

FIXTURE = Path(__file__).parents[1] / "fixtures" / "html" / "village_overview.html"
GAME_CSS = """
#show_summary .visual { position: relative; width: 600px; height: 400px;
  background: linear-gradient(135deg, #6a8f3a, #c2a15a); }
.visual-label { display: inline-block; margin: 4px; padding: 2px 6px; background: #fff; }
"""


async def screenshot_of_fixture(camera: VillageCamera) -> tuple[bytes, int, int] | None:
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch()
        except PlaywrightError as exc:
            pytest.skip(f"chromium indisponível: {exc}")

        page = await browser.new_page()
        await page.route("http*://**/*", lambda route: route.abort())
        await page.goto(FIXTURE.as_uri())
        await page.add_style_tag(content=GAME_CSS)
        shot = await camera.capture(page, "105765")
        await browser.close()
        return (shot.image, shot.width, shot.height) if shot else None


async def test_camera_shoots_only_the_village_illustration() -> None:
    camera = VillageCamera(quality=70, max_bytes=150 * 1024)

    result = await screenshot_of_fixture(camera)

    assert result is not None
    image, width, height = result
    assert image[:3] == b"\xff\xd8\xff"
    assert (width, height) == (600, 400)
    assert "105765" in camera.shots


async def test_camera_lowers_the_quality_until_the_picture_fits() -> None:
    big = await screenshot_of_fixture(VillageCamera(quality=100, max_bytes=10**9))
    small = await screenshot_of_fixture(VillageCamera(quality=100, max_bytes=1))

    assert big is not None and small is not None
    assert len(small[0]) < len(big[0])
