"""Game state repository — writes a full sync snapshot and reads it back."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tribal_assistant.client.scraper.game import GameSnapshot, GameVillage, PlayerSnapshot, ReportSnapshot
from tribal_assistant.models.building import Building
from tribal_assistant.models.command import Command
from tribal_assistant.models.player import Player
from tribal_assistant.models.recruit_order import RecruitOrder
from tribal_assistant.models.report import Report
from tribal_assistant.models.scavenge_option import ScavengeOption
from tribal_assistant.models.unit import Unit
from tribal_assistant.models.village import Village

_VILLAGE_CHILDREN = (
    selectinload(Village.buildings),
    selectinload(Village.units),
    selectinload(Village.recruit_orders),
    selectinload(Village.commands),
    selectinload(Village.scavenge_options),
)


def _naive_utc(value: datetime | None) -> datetime | None:
    return value.astimezone(UTC).replace(tzinfo=None) if value else None


class GameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def persist(self, snapshot: GameSnapshot) -> None:
        now = _naive_utc(datetime.now(UTC))
        await self._upsert_player(snapshot.player, now)
        for village in snapshot.villages:
            await self._upsert_village(village, now)
        await self._upsert_reports(snapshot.reports)
        await self.session.commit()

    async def _upsert_player(self, snap: PlayerSnapshot, now: datetime | None) -> None:
        result = await self.session.execute(select(Player).where(Player.game_id == snap.game_id))
        player = result.scalar_one_or_none()
        if player is None:
            player = Player(game_id=snap.game_id)
            self.session.add(player)
        player.name = snap.name
        player.world = snap.world
        player.ally_id = snap.ally_id
        player.points = snap.points
        player.rank = snap.rank
        player.villages = snap.villages
        player.incomings = snap.incomings
        player.premium_points = snap.premium_points
        player.new_reports = snap.new_reports
        player.new_mails = snap.new_mails
        player.new_quests = snap.new_quests
        player.daily_bonus = snap.daily_bonus
        player.protection_until = _naive_utc(snap.protection_until) or player.protection_until
        player.synced_at = now

    async def _find_village(self, snap: GameVillage) -> Village | None:
        result = await self.session.execute(
            select(Village)
            .where((Village.game_id == snap.game_id) | (Village.coords == snap.coords))
            .options(*_VILLAGE_CHILDREN)
        )
        return result.scalars().first()

    async def _upsert_village(self, snap: GameVillage, now: datetime | None) -> None:
        village = await self._find_village(snap)
        if village is None:
            village = Village(
                buildings=[], units=[], recruit_orders=[], commands=[], scavenge_options=[]
            )
            self.session.add(village)
        village.game_id = snap.game_id
        village.name = snap.name
        village.coords = snap.coords
        village.is_own = True
        village.points = snap.points
        village.wood = snap.wood
        village.clay = snap.clay
        village.iron = snap.iron
        village.storage = snap.storage
        village.pop_current = snap.pop_current
        village.pop_max = snap.pop_max
        village.wood_prod = snap.wood_prod
        village.clay_prod = snap.clay_prod
        village.iron_prod = snap.iron_prod
        village.synced_at = now

        buildings = {b.name: b for b in village.buildings}
        for b in snap.buildings:
            row = buildings.get(b.name)
            if row is None:
                row = Building(name=b.name)
                village.buildings.append(row)
            row.level = b.level
            row.max_level = b.max_level
            row.next_level = b.next_level
            row.next_wood = b.next_wood
            row.next_clay = b.next_clay
            row.next_iron = b.next_iron
            row.next_pop = b.next_pop
            row.build_time = b.build_time
            row.can_build = b.can_build
            row.blocker = b.blocker
            row.target_level = b.queued_level
            row.queued_until = _naive_utc(b.queued_until)

        units = {u.name: u for u in village.units}
        for u in snap.units:
            row = units.get(u.name)
            if row is None:
                row = Unit(name=u.name)
                village.units.append(row)
            row.home = u.home
            row.total = u.total
            row.away = max(u.total - u.home, 0)
            row.available = u.available
            row.max_recruit = u.max_recruit
            row.cost_wood = u.cost_wood
            row.cost_clay = u.cost_clay
            row.cost_iron = u.cost_iron
            row.cost_pop = u.cost_pop
            row.build_time = u.build_time
            row.blocker = u.blocker

        village.recruit_orders = [
            RecruitOrder(unit=r.unit, count=r.count, finishes_at=_naive_utc(r.finishes_at))
            for r in snap.recruit_queue
        ]
        village.commands = [
            Command(
                game_id=c.game_id,
                direction=c.direction,
                kind=c.kind,
                label=c.label,
                coords=c.coords,
                arrival_at=_naive_utc(c.arrival_at),
            )
            for c in snap.commands
        ]

        options = {o.option_id: o for o in village.scavenge_options}
        for s in snap.scavenge:
            row = options.get(s.option_id)
            if row is None:
                row = ScavengeOption(option_id=s.option_id)
                village.scavenge_options.append(row)
            row.name = s.name
            row.loot_factor = s.loot_factor
            row.is_locked = s.is_locked
            row.unlock_at = _naive_utc(s.unlock_at)
            row.return_at = _naive_utc(s.return_at)
            row.squad_json = s.squad_json

    async def _upsert_reports(self, reports: Sequence[ReportSnapshot]) -> None:
        if not reports:
            return
        result = await self.session.execute(
            select(Report).where(Report.game_id.in_([r.game_id for r in reports]))
        )
        existing = {r.game_id: r for r in result.scalars().all()}
        for snap in reports:
            row = existing.get(snap.game_id)
            if row is None:
                row = Report(game_id=snap.game_id)
                self.session.add(row)
            row.title = snap.title
            row.category = snap.category
            row.result = snap.result
            row.is_new = snap.is_new
            row.received_at = _naive_utc(snap.received_at) or row.received_at
            if snap.origin_coords or snap.target_coords:
                row.origin_coords = snap.origin_coords
                row.target_coords = snap.target_coords
                row.loot_wood = snap.loot_wood
                row.loot_clay = snap.loot_clay
                row.loot_iron = snap.loot_iron
                row.haul_total = snap.haul_total

    async def report_ids(self) -> set[str]:
        result = await self.session.execute(select(Report.game_id))
        return set(result.scalars().all())

    async def player(self) -> Player | None:
        result = await self.session.execute(
            select(Player).order_by(Player.synced_at.desc().nulls_last())
        )
        return result.scalars().first()

    async def own_villages(self) -> Sequence[Village]:
        result = await self.session.execute(
            select(Village)
            .where(Village.is_own.is_(True))
            .order_by(Village.coords)
            .options(*_VILLAGE_CHILDREN)
        )
        return result.scalars().all()

    async def reports(self, limit: int = 50) -> Sequence[Report]:
        result = await self.session.execute(
            select(Report).order_by(Report.received_at.desc().nulls_last()).limit(limit)
        )
        return result.scalars().all()
