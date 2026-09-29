"""Achievements screen (Perfil → Realizações): every challenge with its level and progress."""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

LEVEL = re.compile(r"\s*\((?P<tier>[^)]*?)\s*-\s*Nível\s*(?P<level>\d+)\)\s*$")
PROGRESS = re.compile(r"([\d.]+)\s*/\s*([\d.]+)")


class AwardsParser:
    @staticmethod
    def number(text: str) -> int:
        return int(text.replace(".", "") or 0)

    @classmethod
    def parse(cls, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        for group in soup.select(".award-group"):
            head = group.select_one(".award-group-head")
            group_name = head.get_text(" ", strip=True) if head else ""
            for box in group.select(".award-box"):
                item = cls._item(box, group_name)
                if item:
                    items.append(item)

        return items

    @classmethod
    def _item(cls, box: Tag, group: str) -> dict[str, Any] | None:
        title = box.select_one(".award-desc strong")
        if title is None:
            return None

        full = title.get_text("", strip=True)
        level = LEVEL.search(full)
        name = LEVEL.sub("", full).strip() if level else full
        texts = [p.get_text("", strip=True) for p in box.select(".award-desc p")]
        achieved = [t for t in texts if not t.startswith("Próximo nível:")]
        upcoming = next((t.removeprefix("Próximo nível:").strip() for t in texts if t.startswith("Próximo nível:")), None)

        label = box.select_one(".progress-bar .label")
        current = target = None
        if label is not None:
            found = PROGRESS.search(label.get_text("", strip=True))
            if found:
                current, target = cls.number(found.group(1)), cls.number(found.group(2))

        badge = box.select_one(".award")
        earned = bool(badge and any(c.startswith("level") and c != "level0" for c in badge.get("class", [])))

        return {
            "group": group,
            "name": name,
            "tier": level.group("tier") if level else None,
            "level": int(level.group("level")) if level else (1 if earned else 0),
            "description": upcoming or (achieved[0] if achieved else ""),
            "current": current,
            "target": target,
            "earned": earned,
            "done": earned and upcoming is None and (target is None or (current or 0) >= target),
        }
