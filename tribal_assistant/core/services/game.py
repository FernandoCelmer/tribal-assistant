"""Game overview service — everything the dashboard shows, in one read."""

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.db.session import get_session
from tribal_assistant.core.models.player import Player
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.repositories.game import GameRepository
from tribal_assistant.core.schemas.game import (
    BuildingOut,
    CommandOut,
    GameOverview,
    PlayerOut,
    RecommendationOut,
    RecruitOrderOut,
    ReportOut,
    ScavengeOut,
    UnitOut,
    VillageOverview,
)
from tribal_assistant.core.services.advisor import BUILDING_LABELS, label, recommend


def _aware(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=UTC) if value else None


def _building_order(name: str) -> int:
    order = list(BUILDING_LABELS)
    return order.index(name) if name in order else len(order)


def _player(player: Player) -> PlayerOut:
    return PlayerOut(
        name=player.name,
        world=player.world,
        points=player.points,
        rank=player.rank,
        villages=player.villages,
        incomings=player.incomings,
        premium_points=player.premium_points,
        new_reports=player.new_reports,
        new_mails=player.new_mails,
        new_quests=player.new_quests,
        daily_bonus=player.daily_bonus,
        protection_until=_aware(player.protection_until),
        synced_at=_aware(player.synced_at),
    )


def _village(v: Village) -> VillageOverview:
    incoming_attacks = sum(1 for c in v.commands if c.direction == "in" and c.kind in ("attack", "noble"))
    return VillageOverview(
        id=v.id,
        game_id=v.game_id,
        name=v.name,
        coords=v.coords,
        points=v.points,
        wood=v.wood,
        clay=v.clay,
        iron=v.iron,
        storage=v.storage,
        pop_current=v.pop_current,
        pop_max=v.pop_max,
        wood_prod=v.wood_prod,
        clay_prod=v.clay_prod,
        iron_prod=v.iron_prod,
        synced_at=_aware(v.synced_at),
        buildings=[
            BuildingOut(
                name=b.name,
                label=label(b.name),
                level=b.level,
                max_level=b.max_level,
                next_level=b.next_level,
                next_wood=b.next_wood,
                next_clay=b.next_clay,
                next_iron=b.next_iron,
                next_pop=b.next_pop,
                build_time=b.build_time,
                can_build=b.can_build,
                blocker=b.blocker,
                queued_level=b.target_level,
                queued_until=_aware(b.queued_until),
            )
            for b in sorted(v.buildings, key=lambda b: _building_order(b.name))
        ],
        units=[
            UnitOut(
                name=u.name,
                home=u.home,
                total=u.total,
                away=u.away,
                available=u.available,
                max_recruit=u.max_recruit,
                cost_wood=u.cost_wood,
                cost_clay=u.cost_clay,
                cost_iron=u.cost_iron,
                cost_pop=u.cost_pop,
                build_time=u.build_time,
                blocker=u.blocker,
            )
            for u in v.units
        ],
        recruit_orders=[
            RecruitOrderOut(unit=r.unit, count=r.count, finishes_at=_aware(r.finishes_at))
            for r in v.recruit_orders
        ],
        scavenge=[
            ScavengeOut(
                option_id=s.option_id,
                name=s.name,
                loot_factor=s.loot_factor,
                is_locked=s.is_locked,
                unlock_at=_aware(s.unlock_at),
                return_at=_aware(s.return_at),
            )
            for s in sorted(v.scavenge_options, key=lambda s: s.option_id)
        ],
        recommendations=[
            RecommendationOut(**asdict(r))
            for r in recommend(v, v.buildings, incomings=incoming_attacks)
        ],
    )


class GameService:
    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        self.repository = GameRepository(session)

    async def overview(self) -> GameOverview:
        player = await self.repository.player()
        villages = await self.repository.own_villages()
        reports = await self.repository.reports()
        commands = sorted(
            (
                CommandOut(
                    village_coords=v.coords,
                    direction=c.direction,
                    kind=c.kind,
                    label=c.label,
                    coords=c.coords,
                    arrival_at=_aware(c.arrival_at),
                )
                for v in villages
                for c in v.commands
            ),
            key=lambda c: c.arrival_at,
        )
        return GameOverview(
            player=_player(player) if player else None,
            villages=[_village(v) for v in villages],
            commands=commands,
            reports=[
                ReportOut(
                    game_id=r.game_id,
                    title=r.title,
                    category=r.category,
                    result=r.result,
                    is_new=r.is_new,
                    received_at=_aware(r.received_at),
                    origin_coords=r.origin_coords,
                    target_coords=r.target_coords,
                    loot_wood=r.loot_wood,
                    loot_clay=r.loot_clay,
                    loot_iron=r.loot_iron,
                    haul_total=r.haul_total,
                )
                for r in reports
            ],
        )
