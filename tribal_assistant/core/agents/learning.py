"""Turns what happens in the game into lessons stored in the database, and reads them back for the agents."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.clock import Clock
from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.target_intel import TargetIntel
from tribal_assistant.core.game.scraper.awards import AwardsParser
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.models.world import WorldAlly, WorldPlayer, WorldVillage
from tribal_assistant.core.repositories.lessons import LessonRepository

CHALLENGES = "challenges"
REQUIREMENT = re.compile(r"deve ter pelo menos|precisa (?:de|ter)|requer|requisito|nível mínimo|não atend", re.I)

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

    async def blocked(self, action: str, arguments: dict[str, Any], knobs: Knobs | None = None) -> str | None:
        knobs = knobs or Knobs()
        key = f"attempt:{self.signature(action, arguments)}"
        row = await self.repo.recent_failure(key, knobs.int("learning.repeat_window_minutes"), knobs.int("learning.repeat_limit"))
        if row is not None:
            return f"RECUSADO: aprendido — {action} falhou {row.failed}x com os mesmos argumentos: {row.text[:120]}"

        row = await self.repo.get(key)
        window = timedelta(hours=knobs.get("learning.requirement_hours") * max(1, row.failed if row else 1))
        if row is not None and row.failed and REQUIREMENT.search(row.text or "") and datetime.now(UTC).replace(tzinfo=None) - row.last_seen < window:
            return f"RECUSADO: aprendido — o jogo pede um requisito que ainda falta: {row.text[:120]}"

        return None

    async def action(
        self, agent: str, action: str, arguments: dict[str, Any], ok: bool, result: str
    ) -> None:
        if any(result.startswith(prefix) for prefix in IGNORED):
            return

        args = {k: v for k, v in arguments.items() if k != "reason"}
        attempt = f"attempt:{self.signature(action, arguments)}"

        refused = result.startswith("RECUSADO")
        if ok:
            existing = await self.repo.get(attempt)
            if existing is not None:
                existing.failed = 0
                await self.repo.session.commit()
        elif not refused:
            await self.repo.observe(
                attempt, "attempt", f"{action} {args}", result, {"args": args}, ok=False
            )

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
            data["finished_at"] = datetime.now(UTC).isoformat()

        await self.repo.observe(
            f"quest:{quest_id}",
            "quest",
            title,
            f"{goal_text} — {description[:300]}",
            data,
            commit=False,
        )

    async def reports(self, reports: Any, known: set[str], intel: dict[str, dict[str, Any]] | None = None) -> None:
        intel = intel or {}

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
            detail = intel.get(report.game_id, {})
            data = TargetIntel.merge(past, report, detail)
            await self.repo.observe(
                key,
                "target",
                f"alvo {report.target_coords}",
                TargetIntel.describe(data),
                data,
                ok=None if TargetIntel.probe(detail) else report.result == "green",
                commit=False,
            )

        await self.repo.session.commit()

    async def farm_list(self, rows: list[dict[str, Any]]) -> int:
        """Feed the target lessons from the farm assistant rows; a report already read adds only the farm facts."""
        learned = 0
        for row in rows:
            coords = row.get("coords")
            report = row.get("report_id")
            if not coords or not report:
                continue

            key = f"target:{coords}"
            lesson = await self.repo.get(key)
            past = json.loads(lesson.data or "{}") if lesson else {}
            if past.get("farm_report_id") == report:
                continue

            fresh = await self.repo.get(f"report:{report}") is None
            data = TargetIntel.farm_row(past, row, fresh)
            if lesson is not None and not fresh:
                lesson.data = json.dumps(data, ensure_ascii=False, default=str)
                lesson.text = TargetIntel.describe(data)[:300]
            else:
                await self.repo.observe(key, "target", f"alvo {coords}", TargetIntel.describe(data), data, commit=False)
            learned += 1

        await self.repo.session.commit()
        return learned

    async def screens(self, catalog: Any, names: list[str]) -> None:
        for name in names:
            text = catalog.text(name)
            if text:
                await self.repo.observe(
                    f"screen:{name}", "screen", f"tela {name}", text, commit=False
                )

        if "awards" in names:
            await self.challenges(catalog.path("awards"))

        await self.repo.session.commit()

    async def challenges(self, path: Any) -> None:
        """The achievements screen becomes the list of challenges the agents chase."""

        if not path.exists():
            return

        items = AwardsParser.parse(path.read_text(encoding="utf-8"))
        if items:
            await self.repo.observe(CHALLENGES, "challenges", "Desafios", f"{len(items)} desafios", {"items": items}, commit=False)

    async def texts(self, items: list[tuple[Any, ...]]) -> None:
        for key, topic, title, text, *extra in items:
            if text:
                await self.repo.observe(key, topic, title or key, text, extra[0] if extra else None, commit=False)

        await self.repo.session.commit()

    async def neighbourhood(self, radius: int = 15) -> None:
        """Which tribes and players surround each own village, from the public world files."""

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

        clock = Clock()
        lines = [f"- {r.title} ({r.failed}x, última {clock.relative(r.last_seen)})" for r in rules[:limit]]
        lines += [f"- jogo disse {clock.relative(n.last_seen)}: {n.title}" for n in notices]

        tribes = await self.repo.list("tribe", limit=1)
        if tribes:
            lines += [f"- vizinhança: {line}" for line in tribes[0].text.splitlines()[:3]]
        return "Aprendizados:\n" + "\n".join(lines) if lines else ""
