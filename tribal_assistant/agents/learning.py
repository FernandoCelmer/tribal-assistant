"""Turns what happens in the game into lessons stored in the database, and reads them back for the agents."""

import hashlib
import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.repositories.lessons import LessonRepository

REPEAT_WINDOW_MINUTES = 20
REPEAT_LIMIT = 2
IGNORED = ("(simulação)",)


class LessonBook:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = LessonRepository(session)

    @staticmethod
    def normalize(text: str) -> str:
        text = re.sub(r"\d+", "N", text.strip().lower())
        return re.sub(r"\s+", " ", text)[:120]

    @staticmethod
    def signature(action: str, arguments: dict[str, Any]) -> str:
        args = {k: v for k, v in arguments.items() if k != "reason"}
        digest = hashlib.sha1(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[:10]
        return f"{action}:{digest}"

    async def blocked(self, action: str, arguments: dict[str, Any]) -> str | None:
        row = await self.repo.recent_failure(
            f"attempt:{self.signature(action, arguments)}", REPEAT_WINDOW_MINUTES, REPEAT_LIMIT
        )
        if row is None:
            return None

        return f"RECUSADO: aprendido — {action} com os mesmos argumentos falhou {row.failed}x: {row.text}"

    async def action(self, agent: str, action: str, arguments: dict[str, Any], ok: bool, result: str) -> None:
        if any(result.startswith(prefix) for prefix in IGNORED):
            return

        args = {k: v for k, v in arguments.items() if k != "reason"}
        attempt = f"attempt:{self.signature(action, arguments)}"

        if ok:
            existing = await self.repo.get(attempt)
            if existing is not None:
                existing.failed = 0
                await self.repo.session.commit()
        else:
            await self.repo.observe(attempt, "attempt", f"{action} {args}", result, {"args": args}, ok=False)

        refused = result.startswith("RECUSADO")
        topic = "rule" if not ok else "action"
        key = f"{topic}:{action}:{self.normalize(result) if not ok else 'ok'}"
        title = f"{action}: {result}" if not ok else f"{action} funciona"
        await self.repo.observe(
            key,
            topic,
            title,
            result,
            {"agent": agent, "last_args": args, "refused": refused},
            ok=ok,
        )

    async def notices(self, action: str, notices: list[str]) -> None:
        for text in notices:
            clean = " ".join(text.split())
            await self.repo.observe(
                f"notice:{self.normalize(clean)}", "notice", clean[:255], clean, {"after": action}
            )

    async def quest(self, quest_id: str, title: str, state: str, goals: list[dict[str, Any]], description: str) -> None:
        goal_text = "; ".join(
            f"{g.get('title', '')} {g.get('current')}/{g.get('target')}".strip() if g.get("target") else g.get("title", "")
            for g in goals
        )
        data: dict[str, Any] = {"state": state, "goals": goals}
        row = await self.repo.get(f"quest:{quest_id}")
        if state == "finished" and (row is None or json.loads(row.data or "{}").get("state") != "finished"):
            from datetime import UTC, datetime

            data["finished_at"] = datetime.now(UTC).isoformat()

        await self.repo.observe(
            f"quest:{quest_id}", "quest", title, f"{goal_text} — {description[:300]}", data, commit=False
        )

    async def reports(self, reports: Any, known: set[str]) -> None:
        for report in reports:
            if report.game_id in known:
                continue

            await self.repo.observe(
                f"report:{report.game_id}",
                "report",
                report.title,
                report.title,
                {"category": report.category, "result": report.result, "received_at": report.received_at},
                commit=False,
            )

            if not report.target_coords:
                continue

            key = f"target:{report.target_coords}"
            row = await self.repo.get(key)
            past = json.loads(row.data) if row else {}
            haul = report.haul_total if report.haul_total is not None else (
                report.loot_wood + report.loot_clay + report.loot_iron
            )
            attacks = int(past.get("attacks", 0)) + 1
            total = int(past.get("total_haul", 0)) + haul
            await self.repo.observe(
                key,
                "target",
                f"alvo {report.target_coords}",
                f"último resultado {report.result or '?'}, saque {haul}, média {total // attacks}",
                {"last_result": report.result, "last_haul": haul, "attacks": attacks, "total_haul": total, "avg_haul": total // attacks},
                ok=report.result == "green",
                commit=False,
            )

        await self.repo.session.commit()

    async def screens(self, catalog: Any, names: list[str]) -> None:
        for name in names:
            text = catalog.text(name)
            if text:
                await self.repo.observe(f"screen:{name}", "screen", f"tela {name}", text, commit=False)

        await self.repo.session.commit()

    async def target(self, coords: str) -> dict[str, Any]:
        row = await self.repo.get(f"target:{coords}")
        return json.loads(row.data) if row else {}

    async def summary(self, limit: int = 8) -> str:
        rules = [r for r in await self.repo.list("rule", limit=50) if r.failed]
        rules.sort(key=lambda r: -r.failed)
        notices = await self.repo.list("notice", limit=5)

        lines = [f"- {r.title} ({r.failed}x)" for r in rules[:limit]]
        lines += [f"- jogo disse: {n.title}" for n in notices]
        return "Aprendizados:\n" + "\n".join(lines) if lines else ""
