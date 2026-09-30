"""Social memory in the database: conversations, contacts made, messages sent and who the other player is."""

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.accounts.context import current_account
from tribal_assistant.core.agents.social.rules import SocialRules, same
from tribal_assistant.core.models.agent import AgentDecision
from tribal_assistant.core.models.lesson import Lesson
from tribal_assistant.core.models.player import Player
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.models.world import WorldAlly, WorldPlayer, WorldVillage
from tribal_assistant.core.repositories.lessons import LessonRepository

if TYPE_CHECKING:
    from tribal_assistant.core.agents.knobs import Knobs

SENDS = ("reply_mail", "send_mail", "reply_forum")
SOCIAL = (*SENDS, "accept_friend", "add_friend", "apply_to_tribe", "accept_tribe_invite", "accept_mentor")
PENDING = "pendente"
MENTOR = "social:mentor"
TRIBE_MEMBERS = "tribe:members"
FRIENDS = "social:friends"


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def load(row: Lesson | None) -> dict[str, Any]:
    return json.loads(row.data or "{}") if row is not None else {}


class SocialLedger:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LessonRepository(session)

    async def managed(self) -> set[str]:
        """Players of the other accounts this assistant runs in the same world: never talk to them."""
        account = current_account()
        rows = await self.session.execute(
            select(Player.name).where(Player.world == account.server, Player.account_id != account.id).execution_options(all_accounts=True)
        )
        return set(rows.scalars().all())

    async def sent_since(self, hours: float) -> int:
        since = now() - timedelta(hours=hours)
        stmt = select(func.count(AgentDecision.id)).where(
            AgentDecision.action.in_(SENDS), AgentDecision.ok.is_(True), AgentDecision.dry_run.is_(False), AgentDecision.created_at >= since
        )
        return int((await self.session.execute(stmt)).scalar_one())

    @staticmethod
    def contact_key(name: str) -> str:
        return f"contact:{name.strip().casefold()}"[:255]

    async def contact(self, name: str) -> dict[str, Any]:
        return load(await self.repo.get(self.contact_key(name)))

    async def contacts(self) -> list[tuple[Lesson, dict[str, Any]]]:
        rows = (await self.session.execute(select(Lesson).where(Lesson.topic == "contact"))).scalars().all()
        return [(row, load(row)) for row in rows]

    async def first_contacts_since(self, hours: float) -> int:
        since = now() - timedelta(hours=hours)
        return sum(1 for row, data in await self.contacts() if data.get("origin") == "us" and row.first_seen >= since)

    async def unanswered_share(self, days: float = 7, grace_hours: float = 24) -> float | None:
        start, end = now() - timedelta(days=days), now() - timedelta(hours=grace_hours)
        ours = [data for row, data in await self.contacts() if data.get("origin") == "us" and start <= row.first_seen <= end]
        if not ours:
            return None
        return sum(1 for data in ours if not data.get("heard")) / len(ours)

    async def record_sent(self, name: str, kind: str, player_id: str | None = None) -> None:
        data = await self.contact(name)
        stamp = now().isoformat(timespec="minutes")
        data = {
            "name": name,
            "player_id": player_id or data.get("player_id"),
            "origin": data.get("origin") or ("them" if kind == "reply" else "us"),
            "sent": int(data.get("sent") or 0) + 1,
            "heard": int(data.get("heard") or 0),
            "kinds": sorted({*data.get("kinds", []), kind}),
            "last_sent": stamp,
            "last_heard": data.get("last_heard"),
        }
        await self.repo.observe(self.contact_key(name), "contact", name, f"{kind} em {stamp}", data)

    async def record_heard(self, name: str, player_id: str | None = None) -> None:
        data = await self.contact(name)
        stamp = now().isoformat(timespec="minutes")
        data = {
            "name": name,
            "player_id": player_id or data.get("player_id"),
            "origin": data.get("origin") or "them",
            "sent": int(data.get("sent") or 0),
            "heard": int(data.get("heard") or 0) + 1,
            "kinds": data.get("kinds", []),
            "last_sent": data.get("last_sent"),
            "last_heard": stamp,
        }
        await self.repo.observe(self.contact_key(name), "contact", name, f"resposta em {stamp}", data, commit=False)

    async def thread(self, mail_id: str) -> dict[str, Any]:
        return load(await self.repo.get(f"mail:{mail_id}"))

    async def threads(self, limit: int = 20) -> list[dict[str, Any]]:
        return [load(row) | {"id": row.key.split(":", 1)[1]} for row in await self.repo.list("mail", limit=limit)]

    async def save_thread(self, mail: dict[str, Any], thread: dict[str, Any], extra: dict[str, Any]) -> None:
        messages = thread.get("messages") or []
        transcript = "\n".join(f"{m.get('author') or '?'} ({m.get('date') or '-'}): {m.get('text', '')}" for m in messages)
        data = {**mail, "messages": messages, "heard": len(messages), **extra}
        await self.repo.observe(f"mail:{mail['id']}", "mail", str(mail.get("subject") or mail["id"]), transcript or str(mail.get("subject", "")), data)

    async def decide(self, mail_id: str, decision: str, why: str) -> None:
        row = await self.repo.get(f"mail:{mail_id}")
        if row is None:
            return
        await self.repo.observe(row.key, "mail", row.title, row.text, {"decision": {"what": decision, "why": why, "at": now().isoformat(timespec="minutes")}})

    async def note(self, key: str, title: str, text: str = "", data: dict[str, Any] | None = None) -> None:
        await self.repo.observe(key, "social", title, text, data)

    async def get(self, key: str) -> dict[str, Any]:
        return load(await self.repo.get(key))

    async def last_social_action(self) -> datetime | None:
        stmt = select(func.max(AgentDecision.created_at)).where(AgentDecision.action.in_(SOCIAL), AgentDecision.ok.is_(True), AgentDecision.dry_run.is_(False))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def photos(stored: dict[str, Any]) -> list[dict[str, Any]]:
        if stored.get("history"):
            return list(stored["history"])
        return [{"at": stored["at"], "points": stored.get("points") or {}}] if stored.get("at") else []

    async def rates(self, kind: str, current: dict[str, int], min_hours: float, window_hours: float) -> dict[str, float]:
        """Points per hour against the oldest photo at least `min_hours` old; a new photo once the last one is that old."""
        key = f"snapshot:{kind}"
        moment = now()
        photos = [p for p in self.photos(load(await self.repo.get(key))) if moment - datetime.fromisoformat(p["at"]) <= timedelta(hours=window_hours)]

        rates: dict[str, float] = {}
        for photo in photos:
            hours = (moment - datetime.fromisoformat(photo["at"])).total_seconds() / 3600
            if hours >= min_hours:
                before = {str(k): int(v) for k, v in (photo.get("points") or {}).items()}
                rates = {k: round((v - before[k]) / hours, 2) for k, v in current.items() if k in before}
                break

        if not photos or moment - datetime.fromisoformat(photos[-1]["at"]) >= timedelta(hours=min_hours):
            photos.append({"at": moment.isoformat(), "points": current})
            await self.repo.observe(key, "social", f"pontos de {kind}", f"{len(photos)} foto(s)", {"history": photos, "points": None, "at": None})
        return rates

    async def applications(self) -> list[dict[str, Any]]:
        rows = (await self.session.execute(select(Lesson).where(Lesson.topic == "application"))).scalars().all()
        return [load(row) | {"first_seen": row.first_seen} for row in rows]

    async def set_application(self, ally_id: str, tag: str, status: str) -> None:
        data = {"ally_id": ally_id, "tag": tag, "status": status, "at": now().isoformat(timespec="minutes")}
        await self.repo.observe(f"application:{ally_id}", "application", f"candidatura {tag or ally_id}", status, data)

    async def rebuild(self) -> list[str]:
        """Bring back applications and the mentor taken before this ledger existed, from the decisions and lessons kept."""
        found: dict[str, tuple[str, str, datetime]] = {}
        mentor: str | None = None
        rows = await self.session.execute(
            select(AgentDecision.action, AgentDecision.arguments, AgentDecision.created_at)
            .where(AgentDecision.action.in_(("apply_to_tribe", "accept_mentor")), AgentDecision.ok.is_(True), AgentDecision.dry_run.is_(False))
            .order_by(AgentDecision.created_at)
        )
        for action, arguments, at in rows.all():
            args = json.loads(arguments or "{}") if isinstance(arguments, str) else (arguments or {})
            if action == "apply_to_tribe" and str(args.get("ally_id") or "").isdigit():
                found[str(args["ally_id"])] = (str(args.get("tag") or ""), action, at)
            elif action == "accept_mentor" and args.get("name"):
                mentor = str(args["name"])

        for key, action in (("action:apply_to_tribe:ok", "apply_to_tribe"), ("action:accept_mentor:ok", "accept_mentor")):
            lesson = await self.repo.get(key)
            args = load(lesson).get("last_args") or {}
            if lesson is None:
                continue
            if action == "apply_to_tribe" and str(args.get("ally_id") or "").isdigit():
                found.setdefault(str(args["ally_id"]), (str(args.get("tag") or ""), action, lesson.last_seen))
            elif action == "accept_mentor" and args.get("name"):
                mentor = mentor or str(args["name"])

        restored = []
        for ally_id, (tag, _, at) in found.items():
            if await self.repo.get(f"application:{ally_id}") is not None:
                continue
            tag = tag or await self.tribe_tag(ally_id) or ""
            row = await self.repo.observe(
                f"application:{ally_id}",
                "application",
                f"candidatura {tag or ally_id}",
                PENDING,
                {"ally_id": ally_id, "tag": tag, "status": PENDING, "at": at.isoformat(timespec="minutes"), "rebuilt": True},
                commit=False,
            )
            row.first_seen = at
            restored.append(f"candidatura {tag or ally_id}")

        if mentor and not (await self.get(MENTOR)).get("name"):
            await self.repo.observe(MENTOR, "social", "mentor", mentor, {"name": mentor, "rebuilt": True}, commit=False)
            restored.append(f"mentor {mentor}")

        await self.session.commit()
        return restored

    async def tribe_tag(self, ally_id: str | None) -> str | None:
        if not ally_id or not str(ally_id).isdigit():
            return None
        ally = (await self.session.execute(select(WorldAlly).where(WorldAlly.id == int(ally_id)))).scalars().first()
        return ally.tag if ally else None

    async def facts(self, player: dict[str, Any] | None, villages: int, role: str) -> dict[str, Any]:
        """The account's own facts and the social decisions it really took, for every text the model writes."""
        player = player or {}
        applications = [{"tribo": a.get("tag"), "estado": a.get("status")} for a in await self.applications()]
        decisions = {
            "candidaturas": applications,
            "amigos": (await self.get(FRIENDS)).get("count", 0),
            "mentor": (await self.get(MENTOR)).get("name"),
        }
        return {
            "meu_nome": player.get("name"),
            "mundo": player.get("world"),
            "pontos": player.get("points"),
            "ranking": player.get("rank"),
            "aldeias": villages,
            "ataques_chegando": player.get("incomings"),
            "foco_atual": role,
            "tribo": await self.tribe_tag(player.get("ally_id")),
            "decisoes_reais": decisions,
        }

    async def save_tribe(self, part: str, title: str, text: str, data: dict[str, Any]) -> None:
        await self.repo.observe(f"tribe:{part}", "tribe", title, text, data)

    async def managed_allies(self) -> set[str]:
        account = current_account()
        rows = await self.session.execute(
            select(Player.ally_id).where(Player.world == account.server, Player.account_id != account.id).execution_options(all_accounts=True)
        )
        return {str(a) for a in rows.scalars().all() if a}

    async def around(self, radius: int) -> list[tuple[WorldPlayer, float]]:
        """Players with a village within the radius of an own village, closest distance first."""
        coords = await self.own_coords()
        if not coords:
            return []
        xs, ys = [x for x, _ in coords], [y for _, y in coords]
        rows = (
            await self.session.execute(
                select(WorldVillage, WorldPlayer)
                .join(WorldPlayer, WorldPlayer.id == WorldVillage.player_id)
                .where(WorldVillage.x.between(min(xs) - radius, max(xs) + radius), WorldVillage.y.between(min(ys) - radius, max(ys) + radius))
            )
        ).all()
        closest: dict[int, tuple[WorldPlayer, float]] = {}
        for village, player in rows:
            distance = min(((village.x - x) ** 2 + (village.y - y) ** 2) ** 0.5 for x, y in coords)
            if distance > radius or distance == 0:
                continue
            if player.id not in closest or distance < closest[player.id][1]:
                closest[player.id] = (player, round(distance, 1))
        return sorted(closest.values(), key=lambda item: item[1])

    @staticmethod
    def activity(player: WorldPlayer, rate: float | None, knobs: "Knobs", points: int) -> str | None:
        """Why a player counts as active: the measured pace, or while there is none, the world data."""
        if rate is not None:
            return f"{rate:g} pts/h" if rate >= knobs.get("social.active_growth") else None
        if player.villages > 1:
            return f"{player.villages} aldeias"
        if points and player.points >= knobs.get("social.active_share") * points:
            return f"{player.points} pts, no ritmo da conta"
        return None

    async def active_neighbours(self, knobs: "Knobs", skip: set[str], points: int = 0) -> list[dict[str, Any]]:
        around = await self.around(knobs.int("social.neighbour_radius"))
        rates = await self.rates("players", {str(p.id): p.points for p, _ in around}, knobs.get("social.snapshot_hours"), knobs.get("social.activity_window_hours"))
        active = []
        for p, d in around:
            rate = rates.get(str(p.id))
            why = self.activity(p, rate, knobs, points)
            if why and not any(same(p.name, s) for s in skip):
                active.append({"name": p.name, "player_id": str(p.id), "points": p.points, "distance": d, "rate": rate, "why": why})
        return sorted(active, key=lambda n: (n["distance"], -(n["rate"] or 0)))

    async def nearby_tribes(self, knobs: "Knobs") -> list[dict[str, Any]]:
        around = await self.around(knobs.int("diplomacy.search_radius"))
        ally_ids = {p.ally_id for p, _ in around if p.ally_id}
        if not ally_ids:
            return []
        allies = (await self.session.execute(select(WorldAlly).where(WorldAlly.id.in_(ally_ids)))).scalars().all()
        growth = await self.rates("allies", {str(a.id): a.points for a in allies}, knobs.get("social.snapshot_hours"), knobs.get("social.activity_window_hours"))
        return [
            {
                "id": str(a.id),
                "tag": a.tag,
                "members": a.members,
                "points": a.points,
                "rank": a.rank,
                "growth": growth.get(str(a.id)),
                "score": int(growth.get(str(a.id), 0) >= knobs.get("social.active_growth")),
            }
            for a in allies
        ]

    async def top_member(self, ally_id: str) -> WorldPlayer | None:
        if not str(ally_id).isdigit():
            return None
        stmt = select(WorldPlayer).where(WorldPlayer.ally_id == int(ally_id)).order_by(WorldPlayer.points.desc()).limit(1)
        return (await self.session.execute(stmt)).scalars().first()

    async def own_coords(self) -> list[tuple[int, int]]:
        rows = (await self.session.execute(select(Village.coords).where(Village.is_own.is_(True)))).scalars().all()
        coords = []
        for text in rows:
            x, _, y = (text or "").partition("|")
            if x.isdigit() and y.isdigit():
                coords.append((int(x), int(y)))
        return coords

    async def distance(self, player_id: int, coords: list[tuple[int, int]]) -> float | None:
        villages = (await self.session.execute(select(WorldVillage.x, WorldVillage.y).where(WorldVillage.player_id == player_id))).all()
        if not villages or not coords:
            return None
        return round(min(((x - ox) ** 2 + (y - oy) ** 2) ** 0.5 for x, y in villages for ox, oy in coords), 1)

    async def card(self, name: str, me: dict[str, Any] | None, knobs: "Knobs") -> dict[str, Any]:
        """Who the other player is, from the public world data and what the account learned."""
        me = me or {}
        player = (await self.session.execute(select(WorldPlayer).where(func.lower(WorldPlayer.name) == name.strip().lower()))).scalars().first()
        mentor = (await self.get(MENTOR)).get("name")
        members = (await self.get(TRIBE_MEMBERS)).get("members") or []
        member = next((m for m in members if same(m.get("name"), name)), None)
        card: dict[str, Any] = {
            "nome": name,
            "mentor": same(mentor, name),
            "leader": bool(member and member.get("leader")),
            "same_tribe": member is not None,
            "known": player is not None,
        }
        if player is None:
            return card

        ally = (await self.session.execute(select(WorldAlly).where(WorldAlly.id == player.ally_id))).scalars().first() if player.ally_id else None
        distance = await self.distance(player.id, await self.own_coords())
        points = int(me.get("points") or 0)
        card.update(
            {
                "player_id": str(player.id),
                "pontos": player.points,
                "ranking": player.rank,
                "aldeias": player.villages,
                "tribo": ally.tag if ally else None,
                "distancia": distance,
                "vizinho": distance is not None and distance <= knobs.get("social.neighbour_radius"),
                "same_tribe": card["same_tribe"] or (bool(me.get("ally_id")) and str(player.ally_id) == str(me.get("ally_id"))),
                "ameaca": distance is not None
                and distance <= knobs.get("threat.danger_distance")
                and player.points >= knobs.get("threat.danger_ratio") * max(points, 1)
                and player.points >= knobs.get("threat.danger_points"),
            }
        )
        card["aliado"] = card["same_tribe"]
        return card

    @staticmethod
    def label(card: dict[str, Any]) -> str:
        tags = [k for k in ("mentor", "leader", "aliado", "vizinho", "ameaca") if card.get(k)]
        return ", ".join(tags) or "desconhecido"

    @staticmethod
    def intent_of(thread: dict[str, Any]) -> str:
        return SocialRules.intent(" ".join(m.get("text", "") for m in thread.get("messages", [])[-2:]))
