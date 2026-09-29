"""Village HTML scraper — pure function of HTML -> dataclass."""

from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class VillageSnapshot:
    name: str
    coords: str
    wood: int
    clay: int
    iron: int
    storage: int
    pop_current: int
    pop_max: int


def _to_int(text: str | None) -> int:
    if not text:
        return 0
    digits = "".join(c for c in text if c.isdigit())
    return int(digits) if digits else 0


def _select_text(soup: BeautifulSoup, selector: str) -> str | None:
    el = soup.select_one(selector)
    return el.text if el else None


def scrape_village(html: str) -> VillageSnapshot:
    soup = BeautifulSoup(html, "lxml")
    name = (_select_text(soup, "#menu_row2_village a span") or "unknown").strip()
    coords = (_select_text(soup, "#menu_row2_village .coord") or "0|0").strip()
    return VillageSnapshot(
        name=name,
        coords=coords,
        wood=_to_int(_select_text(soup, "#wood")),
        clay=_to_int(_select_text(soup, "#stone")),
        iron=_to_int(_select_text(soup, "#iron")),
        storage=_to_int(_select_text(soup, "#storage")),
        pop_current=_to_int(_select_text(soup, "#pop_current_label")),
        pop_max=_to_int(_select_text(soup, "#pop_max_label")),
    )
