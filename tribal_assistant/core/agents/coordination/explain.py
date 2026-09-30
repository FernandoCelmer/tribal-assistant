"""Groups a round's free-text deferrals and results into a few stable kinds the panel can chart."""

from collections import Counter
from typing import Any


class RoundExplainer:
    DEFERRALS = (
        ("vetado", "veto"),
        ("feito há pouco", "recent"),
        ("depende de", "dependency"),
        ("fila de construção cheia", "queue"),
        ("limite de ações", "limit"),
        ("tropas comprometidas", "troops"),
        ("consumiria recursos reservados", "reserved"),
        ("falta população", "population"),
        ("faltam", "resources"),
    )

    @classmethod
    def deferral(cls, why: str) -> str:
        text = why.strip().lower()
        return next((kind for prefix, kind in cls.DEFERRALS if text.startswith(prefix)), "learned")

    @staticmethod
    def outcome(entry: dict[str, Any]) -> str:
        if entry.get("ok"):
            return "ok"

        return "refused" if str(entry.get("result") or "").startswith("RECUSADO") else "failed"

    @classmethod
    def annotate(cls, data: dict[str, Any]) -> dict[str, Any]:
        for entry in data.get("deferred") or []:
            entry["why_kind"] = cls.deferral(str(entry.get("why") or ""))
        for entry in data.get("executed") or []:
            entry["outcome"] = cls.outcome(entry)

        return data

    @classmethod
    def tally(cls, data: dict[str, Any]) -> tuple[Counter[str], Counter[str]]:
        outcomes = Counter(cls.outcome(e) for e in data.get("executed") or [])
        deferrals = Counter(cls.deferral(str(e.get("why") or "")) for e in data.get("deferred") or [])
        return outcomes, deferrals
