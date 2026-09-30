"""Farm assistant screen (am_farm): templates A and B, troops at home and the rows of the latest raids."""

import json
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

TEMPLATES = {"a": 0, "b": 1}
BUTTONS = ("a", "b", "c")
RESOURCES = {"wood": "wood", "stone": "clay", "clay": "clay", "iron": "iron"}
UNIT_FIELD = re.compile(r"^([a-z]+)\[(\d+)\]$")
ROW_ID = re.compile(r"village_(\d+)")
COORDS = re.compile(r"\((\d{1,3})\|(\d{1,3})\)")
REPORT = re.compile(r"[?&]view=(\d+)")
DOT = re.compile(r"dots/([a-z_]+)\.")
MAX_LOOT = re.compile(r"max_loot/(\d)\.")
TEMPLATE_ID = re.compile(r"sendUnits\(\s*this\s*,\s*\d+\s*,\s*(\d+)")
CURRENT_UNITS = re.compile(r"Accountmanager\.farm\.current_units\s*=\s*(\{[^;]*\})\s*;")
NUMBER = re.compile(r"\d[\d.]*")
DECIMAL = re.compile(r"\d+(?:[.,]\d+)?")
PAGE_SIZE_ID = "farm_pagesize"


class FarmAssistantParser:
    """Reads the screen defensively: a missing piece becomes None or an empty value, never an error."""

    @staticmethod
    def number(text: str | None) -> int | None:
        found = NUMBER.search(text or "")
        return int(found.group().replace(".", "")) if found else None

    @staticmethod
    def decimal(text: str | None) -> float | None:
        found = DECIMAL.search(text or "")
        return float(found.group().replace(",", ".")) if found else None

    @classmethod
    def parse(cls, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html or "", "lxml")
        form = soup.select_one('form[action*="action=edit_all"]')
        plunder = soup.select_one("#plunder_list")
        available = form is not None or plunder is not None
        premium = bool(soup.select_one('a[href*="screen=premium"]')) and not available
        size = soup.select_one(f"#{PAGE_SIZE_ID}")

        return {
            "available": available,
            "reason": "" if available else ("pede conta premium" if premium else "tela do assistente de saque não encontrada"),
            "premium_required": premium,
            "templates": cls.templates(soup),
            "home": cls.home(soup, html or ""),
            "targets": [row for row in (cls.row(tr) for tr in soup.select("#plunder_list tr[id^=village_]")) if row],
            "page_size": cls.number(str(size.get("value", ""))) if size else None,
            "hide_attacked": "farm.hide_attacked = true" in (html or ""),
        }

    @classmethod
    def templates(cls, soup: BeautifulSoup) -> dict[str, dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        for letter, index in TEMPLATES.items():
            ident = soup.select_one(f'input[name="template[{index}][id]"]')
            if ident is None:
                continue

            fresh = soup.select_one(f'input[name="template[{index}][new]"]')
            units: dict[str, int] = {}
            for field in soup.select("input[name]"):
                match = UNIT_FIELD.match(str(field.get("name", "")))
                if match and int(match.group(2)) == index:
                    units[match.group(1)] = cls.number(str(field.get("value", ""))) or 0

            found[letter] = {
                "id": str(ident.get("value", "")),
                "new": fresh is not None and str(fresh.get("value", "")) == "1",
                "units": units,
            }

        return found

    @classmethod
    def home(cls, soup: BeautifulSoup, html: str) -> dict[str, int]:
        home: dict[str, int] = {}
        for cell in soup.select("#units_home td.unit-item[data-unit-count]"):
            unit = str(cell.get("id") or "")
            if not unit:
                unit = next((c[len("unit-item-"):] for c in cell.get("class", []) if c.startswith("unit-item-")), "")
            if unit:
                home[unit] = cls.number(str(cell.get("data-unit-count"))) or 0

        if home:
            return home

        match = CURRENT_UNITS.search(html)
        if not match:
            return {}

        try:
            raw = json.loads(match.group(1))
        except ValueError:
            return {}

        return {str(k): int(v) for k, v in raw.items() if str(v).isdigit()}

    @classmethod
    def row(cls, tr: Tag) -> dict[str, Any] | None:
        ident = ROW_ID.search(str(tr.get("id", "")))
        link = tr.select_one('a[href*="screen=report"]')
        coords = COORDS.search(link.get_text(" ", strip=True)) if link else None
        if not ident or not coords:
            return None

        report = REPORT.search(str(link.get("href", ""))) if link else None
        dot = tr.select_one('img[src*="dots/"]')
        color = DOT.search(str(dot.get("src", ""))) if dot else None
        loot = tr.select_one('img[src*="max_loot/"]')
        full = MAX_LOOT.search(str(loot.get("src", ""))) if loot else None

        link_cell = link.find_parent("td") if link else None
        time_cell = link_cell.find_next_sibling("td") if link_cell else None
        resources_cell = tr.select_one('td[colspan="3"]')
        wall_cell = resources_cell.find_next_sibling("td") if resources_cell else None
        distance_cell = wall_cell.find_next_sibling("td") if wall_cell else None

        return {
            "village_id": int(ident.group(1)),
            "coords": f"{coords.group(1)}|{coords.group(2)}",
            "report_id": report.group(1) if report else None,
            "result": color.group(1) if color else None,
            "full": (full.group(1) == "1") if full else None,
            "time": time_cell.get_text(" ", strip=True) if time_cell else "",
            "resources": cls.resources(resources_cell),
            "wall": cls.number(wall_cell.get_text(strip=True)) if wall_cell else None,
            "distance": cls.decimal(distance_cell.get_text(strip=True)) if distance_cell else None,
            "buttons": {letter: cls.enabled(tr, letter) for letter in BUTTONS},
            "template_ids": cls.template_ids(tr),
        }

    @classmethod
    def resources(cls, cell: Tag | None) -> dict[str, int] | None:
        if cell is None:
            return None

        found: dict[str, int] = {}
        for icon in cell.select(".icon, .res"):
            kind = next((RESOURCES[c] for c in icon.get("class", []) if c in RESOURCES), None)
            holder = icon.parent if isinstance(icon.parent, Tag) else None
            if kind is None or holder is None:
                continue

            amount = cls.number(holder.get_text(" ", strip=True))
            if amount is not None:
                found[kind] = amount

        return found or None

    @staticmethod
    def enabled(tr: Tag, letter: str) -> bool:
        button = tr.select_one(f"a.farm_icon_{letter}")
        if button is None:
            return False

        classes = set(button.get("class", []))
        return not classes & {"farm_icon_disabled", "decoration", "done"}

    @staticmethod
    def template_ids(tr: Tag) -> dict[str, str]:
        ids: dict[str, str] = {}
        for letter in TEMPLATES:
            button = tr.select_one(f"a.farm_icon_{letter}")
            match = TEMPLATE_ID.search(str(button.get("onclick", ""))) if button else None
            if match:
                ids[letter] = match.group(1)
        return ids

    @staticmethod
    def target(state: dict[str, Any], coords: str) -> dict[str, Any] | None:
        return next((row for row in state.get("targets") or [] if row.get("coords") == coords), None)

    @staticmethod
    def squad(state: dict[str, Any], letter: str) -> dict[str, int]:
        units = ((state.get("templates") or {}).get(letter) or {}).get("units") or {}
        return {u: int(n) for u, n in units.items() if int(n) > 0}
