"""Public world data files (`/map/*.txt`, `interface.php`), fetched over plain HTTP."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote_plus

import httpx

from tribal_assistant.core.accounts.context import current_account

MAP_FILES = ("village", "player", "ally")
FIGHT_FILES = ("kill_att", "kill_def", "conquer")
INTERFACE_FUNCS = {"config": "get_config", "units": "get_unit_info", "buildings": "get_building_info"}


@dataclass(frozen=True)
class WorldData:
    villages: list[dict[str, Any]]
    players: list[dict[str, Any]]
    allies: list[dict[str, Any]]
    settings: dict[str, Any]
    attack: dict[int, int] = field(default_factory=dict)
    defence: dict[int, int] = field(default_factory=dict)
    conquests: list[dict[str, Any]] = field(default_factory=list)


def _rows(text: str) -> list[list[str]]:
    return [line.split(",") for line in text.splitlines() if line.strip()]


def parse_villages(text: str) -> list[dict[str, Any]]:
    return [
        {
            "id": int(r[0]), "name": unquote_plus(r[1]), "x": int(r[2]), "y": int(r[3]),
            "player_id": int(r[4]), "points": int(r[5]), "bonus_id": int(r[6]) if len(r) > 6 else 0,
        }
        for r in _rows(text)
    ]


def parse_players(text: str) -> list[dict[str, Any]]:
    return [
        {
            "id": int(r[0]), "name": unquote_plus(r[1]), "ally_id": int(r[2]),
            "villages": int(r[3]), "points": int(r[4]), "rank": int(r[5]),
        }
        for r in _rows(text)
    ]


def parse_allies(text: str) -> list[dict[str, Any]]:
    return [
        {
            "id": int(r[0]), "name": unquote_plus(r[1]), "tag": unquote_plus(r[2]),
            "members": int(r[3]), "villages": int(r[4]), "points": int(r[5]),
            "all_points": int(r[6]), "rank": int(r[7]),
        }
        for r in _rows(text)
    ]


def parse_kills(text: str) -> dict[int, int]:
    """`kill_att`/`kill_def`: rank, player id, opponents defeated."""
    return {int(r[1]): int(r[2]) for r in _rows(text) if len(r) >= 3}


def parse_conquests(text: str) -> list[dict[str, Any]]:
    """`conquer`: village id, unix time, new owner, old owner."""
    return [
        {"village_id": int(r[0]), "at": datetime.fromtimestamp(int(r[1]), UTC).replace(tzinfo=None), "new_owner": int(r[2]), "old_owner": int(r[3])}
        for r in _rows(text)
        if len(r) >= 4
    ]


def _xml_value(element: ET.Element) -> Any:
    if len(element):
        return {child.tag: _xml_value(child) for child in element}
    text = (element.text or "").strip()
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            continue
    return text


def parse_xml(text: str) -> dict[str, Any]:
    value = _xml_value(ET.fromstring(text))
    return value if isinstance(value, dict) else {}


async def fetch_world() -> WorldData:
    base = current_account().base_url
    async with httpx.AsyncClient(timeout=60, headers={"User-Agent": "Mozilla/5.0"}) as client:
        files = {}
        for name in MAP_FILES:
            response = await client.get(f"{base}/map/{name}.txt")
            response.raise_for_status()
            files[name] = response.text
        for name in FIGHT_FILES:
            response = await client.get(f"{base}/map/{name}.txt")
            files[name] = response.text if response.status_code == 200 else ""
        world_settings = {}
        for key, func in INTERFACE_FUNCS.items():
            response = await client.get(f"{base}/interface.php", params={"func": func})
            response.raise_for_status()
            world_settings[key] = parse_xml(response.text)
    return WorldData(
        villages=parse_villages(files["village"]),
        players=parse_players(files["player"]),
        allies=parse_allies(files["ally"]),
        settings=world_settings,
        attack=parse_kills(files["kill_att"]),
        defence=parse_kills(files["kill_def"]),
        conquests=parse_conquests(files["conquer"]),
    )
