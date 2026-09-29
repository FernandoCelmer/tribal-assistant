"""What the reports taught about one barbarian target, kept in the `data` of its lesson."""

from datetime import UTC, datetime
from typing import Any

KEPT_BUILDINGS = ("wood", "stone", "iron", "storage", "hide", "wall")


class TargetIntel:
    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def probe(detail: dict[str, Any]) -> bool:
        """Only scouts went: the report teaches the target, not how a raid went."""
        sent = detail.get("attacker_units") or {}
        return bool(sent) and set(sent) <= {"spy"}

    @staticmethod
    def remaining(detail: dict[str, Any]) -> int:
        units = detail.get("defender_units") or {}
        losses = detail.get("defender_losses") or {}
        return sum(max(0, n - losses.get(u, 0)) for u, n in units.items())

    @classmethod
    def merge(cls, past: dict[str, Any], report: Any, detail: dict[str, Any]) -> dict[str, Any]:
        data = dict(past)
        stamp = cls.now()

        if cls.probe(detail):
            data["last_probe"] = report.result
            data["probed_at"] = stamp
        else:
            haul = report.haul_total if report.haul_total is not None else report.loot_wood + report.loot_clay + report.loot_iron
            attacks = int(past.get("attacks", 0)) + 1
            total = int(past.get("total_haul", 0)) + haul
            data.update(
                {
                    "last_result": report.result,
                    "last_haul": haul,
                    "attacks": attacks,
                    "total_haul": total,
                    "avg_haul": total // attacks,
                    "yellow_streak": int(past.get("yellow_streak", 0)) + 1 if report.result in ("yellow", "red") else 0,
                    "looted_at": stamp,
                }
            )
            if "attacker_units" in detail:
                data["losses"] = detail.get("attacker_losses") or {}

        if "scouted" in detail:
            data["scouted"] = detail["scouted"]
            data["scouted_at"] = stamp

        if "buildings" in detail:
            data["wall"] = int(detail.get("wall") or 0)
            data["buildings"] = {k: v for k, v in detail["buildings"].items() if k in KEPT_BUILDINGS}

        if "defender_units" in detail:
            data["defender_units"] = detail["defender_units"]
            data["defender_losses"] = detail.get("defender_losses") or {}
            data["defenders_left"] = cls.remaining(detail)
            if cls.probe(detail) and data["defenders_left"] == 0:
                data["yellow_streak"] = 0

        return data

    @staticmethod
    def describe(data: dict[str, Any]) -> str:
        parts = [
            f"último resultado {data.get('last_result') or '?'}",
            f"saque {data.get('last_haul', 0)}",
            f"média {data.get('avg_haul', 0)}",
        ]
        if "wall" in data:
            parts.append(f"muralha {data['wall']}")

        if data.get("scouted"):
            parts.append(f"espionado {sum(data['scouted'].values())} recursos")

        return ", ".join(parts)

    @staticmethod
    def age_hours(data: dict[str, Any], key: str) -> float | None:
        raw = data.get(key)
        if not raw:
            return None

        try:
            stamp = datetime.fromisoformat(str(raw))
        except ValueError:
            return None

        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)

        return max(0.0, (datetime.now(UTC) - stamp).total_seconds() / 3600)

    @classmethod
    def fresh_scouting(cls, data: dict[str, Any]) -> bool:
        """Scouted resources still describe the village: no raid landed after the spies."""
        scouted = cls.age_hours(data, "scouted_at")
        if scouted is None:
            return False

        looted = cls.age_hours(data, "looted_at")
        return looted is None or looted > scouted

    @classmethod
    def summary(cls, coords: str, data: dict[str, Any]) -> dict[str, Any]:
        age = cls.age_hours(data, "scouted_at")
        return {
            "coords": coords,
            "wall": data.get("wall"),
            "scouted": data.get("scouted"),
            "scouted_hours_ago": round(age, 1) if age is not None else None,
            "scouting_fresh": cls.fresh_scouting(data),
            "buildings": data.get("buildings"),
            "defenders_left": data.get("defenders_left"),
            "last_result": data.get("last_result"),
            "last_probe": data.get("last_probe"),
            "avg_haul": data.get("avg_haul"),
            "attacks": data.get("attacks", 0),
            "yellow_streak": data.get("yellow_streak", 0),
            "losses": data.get("losses"),
        }
