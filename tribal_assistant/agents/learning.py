"""Turns what happens in the game into lessons stored in the database, and reads them back for the agents."""

import hashlib
import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.repositories.lessons import LessonRepository

REPEAT_WINDOW_MINUTES = 20
REPEAT_LIMIT = 2
IGNORED = ("(simulação)", "RECUSADO: aprendido")
TEXT_LIMIT = 300


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
        digest = hashlib.sha1(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[
            :10
        ]
        return f"{action}:{digest}"

    async def blocked(self, action: str, arguments: dict[str, Any]) -> str | None:
        row = await self.repo.recent_failure(
            f"attempt:{self.signature(action, arguments)}", REPEAT_WINDOW_MINUTES, REPEAT_LIMIT
        )
        if row is None:
            return None

        return f"RECUSADO: aprendido — {action} falhou {row.failed}x com os mesmos argumentos: {row.text[:120]}"

    async def action(
        self, agent: str, action: str, arguments: dict[str, Any], ok: bool, result: str
    ) -> None:
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
            await self.repo.observe(
                attempt, "attempt", f"{action} {args}", result, {"args": args}, ok=False
            )

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

    async def quest(
        self, quest_id: str, title: str, state: str, goals: list[dict[str, Any]], description: str
    ) -> None:
        goal_text = "; ".join(
            f"{g.get('title', '')} {g.get('current')}/{g.get('target')}".strip()
            if g.get("target")
            else g.get("title", "")
            for g in goals
        )
        data: dict[str, Any] = {"state": state, "goals": goals}
        row = await self.repo.get(f"quest:{quest_id}")
        if state == "finished" and (
            row is None or json.loads(row.data or "{}").get("state") != "finished"
        ):
            from datetime import UTC, datetime

            data["finished_at"] = datetime.now(UTC).isoformat()

        await self.repo.observe(
            f"quest:{quest_id}",
            "quest",
            title,
            f"{goal_text} — {description[:300]}",
            data,
            commit=False,
        )

    async def reports(self, reports: Any, known: set[str]) -> None:
        for report in reports:
            if report.game_id in known:
                continue

            await self.repo.observe(
                f"report:{report.game_id}",
                "report",
                report.title,
                "",
                {
                    "category": report.category,
                    "result": report.result,
                    "received_at": report.received_at,
                },
                commit=False,
            )

            if not report.target_coords:
                continue

            key = f"target:{report.target_coords}"
            row = await self.repo.get(key)
            past = json.loads(row.data) if row else {}
            haul = (
                report.haul_total
                if report.haul_total is not None
                else (report.loot_wood + report.loot_clay + report.loot_iron)
            )
            attacks = int(past.get("attacks", 0)) + 1
            streak = int(past.get("yellow_streak", 0)) + 1 if report.result in ("yellow", "red") else 0
            total = int(past.get("total_haul", 0)) + haul
            await self.repo.observe(
                key,
                "target",
                f"alvo {report.target_coords}",
                f"último resultado {report.result or '?'}, saque {haul}, média {total // attacks}",
                {
                    "last_result": report.result,
                    "last_haul": haul,
                    "attacks": attacks,
                    "total_haul": total,
                    "avg_haul": total // attacks,
                    "yellow_streak": streak,
                },
                ok=report.result == "green",
                commit=False,
            )

        await self.repo.session.commit()

    async def screens(self, catalog: Any, names: list[str]) -> None:
        for name in names:
            text = catalog.text(name)
            if text:
                await self.repo.observe(
                    f"screen:{name}", "screen", f"tela {name}", text, commit=False
                )

        await self.repo.session.commit()

    async def texts(self, items: list[tuple[str, str, str, str]]) -> None:
        for key, topic, title, text in items:
            if text:
                await self.repo.observe(key, topic, title or key, text, commit=False)

        await self.repo.session.commit()

    async def neighbourhood(self, radius: int = 15) -> None:
        """Which tribes and players surround each own village, from the public world files."""
        from sqlalchemy import select

        from tribal_assistant.models.village import Village
        from tribal_assistant.models.world import WorldAlly, WorldPlayer, WorldVillage

        session = self.repo.session
        own = (
            (await session.execute(select(Village).where(Village.is_own.is_(True)))).scalars().all()
        )

        for village in own:
            x, y = (int(n) for n in village.coords.split("|"))
            rows = (
                await session.execute(
                    select(WorldVillage, WorldPlayer, WorldAlly)
                    .join(WorldPlayer, WorldPlayer.id == WorldVillage.player_id)
                    .outerjoin(WorldAlly, WorldAlly.id == WorldPlayer.ally_id)
                    .where(WorldVillage.player_id > 0)
                    .where(WorldVillage.x.between(x - radius, x + radius))
                    .where(WorldVillage.y.between(y - radius, y + radius))
                )
            ).all()

            tribes: dict[str, dict[str, Any]] = {}
            for wv, player, ally in rows:
                if wv.x == x and wv.y == y:
                    continue

                tag = ally.tag if ally else "-"
                distance = round(((wv.x - x) ** 2 + (wv.y - y) ** 2) ** 0.5, 1)
                entry = tribes.setdefault(
                    tag,
                    {
                        "tag": tag,
                        "name": ally.name if ally else "sem tribo",
                        "rank": ally.rank if ally else None,
                        "tribe_points": ally.points if ally else 0,
                        "members": ally.members if ally else 0,
                        "players": set(),
                        "villages": 0,
                        "closest": distance,
                        "strongest_player": 0,
                    },
                )
                entry["players"].add(player.name)
                entry["villages"] += 1
                entry["closest"] = min(entry["closest"], distance)
                entry["strongest_player"] = max(entry["strongest_player"], player.points)

            ranked = sorted(
                tribes.values(), key=lambda t: (t["tag"] == "-", -(t["tribe_points"] or 0))
            )
            for tribe in ranked:
                tribe["players"] = len(tribe["players"])

            lines = [
                f"{t['tag']} ({t['name']}, rank {t['rank'] or '-'}, {t['tribe_points']} pts, {t['members']} membros): "
                f"{t['players']} jogador(es) e {t['villages']} aldeia(s) perto, mais próxima a {t['closest']} campos"
                for t in ranked[:12]
            ]
            await self.repo.observe(
                f"tribes:{village.coords}",
                "tribe",
                f"tribos num raio de {radius} campos de {village.coords}",
                "\n".join(lines),
                {"tribes": ranked[:25]},
                commit=False,
            )

        await session.commit()

    async def target(self, coords: str) -> dict[str, Any]:
        row = await self.repo.get(f"target:{coords}")
        return json.loads(row.data) if row else {}

    async def due(self, name: str, hours: float) -> bool:
        from datetime import UTC, datetime, timedelta

        row = await self.repo.get(f"cooldown:{name}")
        if row is None:
            return True

        return datetime.now(UTC).replace(tzinfo=None) - row.last_seen >= timedelta(hours=hours)

    async def mark(self, name: str, note: str = "") -> None:
        await self.repo.observe(f"cooldown:{name}", "cooldown", name, note)

    async def summary(self, limit: int = 8) -> str:
        rules = [r for r in await self.repo.list("rule", limit=50) if r.failed]
        rules.sort(key=lambda r: -r.failed)
        notices = await self.repo.list("notice", limit=5)

        lines = [f"- {r.title} ({r.failed}x)" for r in rules[:limit]]
        lines += [f"- jogo disse: {n.title}" for n in notices]

        tribes = await self.repo.list("tribe", limit=1)
        if tribes:
            lines += [f"- vizinhança: {line}" for line in tribes[0].text.splitlines()[:3]]
        return "Aprendizados:\n" + "\n".join(lines) if lines else ""
