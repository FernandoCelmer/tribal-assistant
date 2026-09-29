"""Report inbox as synced, newest first, a page at a time."""

from datetime import UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.models.report import Report
from tribal_assistant.core.schemas.game import ReportOut
from tribal_assistant.core.schemas.reports import ReportPage


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def out(row: Report) -> ReportOut:
        return ReportOut(
            game_id=row.game_id,
            title=row.title,
            category=row.category,
            result=row.result,
            is_new=row.is_new,
            received_at=row.received_at.replace(tzinfo=UTC) if row.received_at else None,
            origin_coords=row.origin_coords,
            target_coords=row.target_coords,
            loot_wood=row.loot_wood,
            loot_clay=row.loot_clay,
            loot_iron=row.loot_iron,
            haul_total=row.haul_total,
        )

    async def page(self, offset: int = 0, limit: int = 50, category: str | None = None, result: str | None = None, coords: str | None = None) -> ReportPage:
        stmt = select(Report)
        if category:
            stmt = stmt.where(Report.category == category)
        if result:
            stmt = stmt.where(Report.result == result)
        if coords:
            stmt = stmt.where((Report.target_coords == coords) | (Report.origin_coords == coords))

        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = await self.session.execute(stmt.order_by(Report.received_at.desc().nulls_last(), Report.id.desc()).offset(offset).limit(limit))
        return ReportPage(total=total, offset=offset, limit=limit, items=[self.out(r) for r in rows.scalars().all()])
