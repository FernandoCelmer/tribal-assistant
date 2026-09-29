"""Hours left of beginner protection, from the synced player."""

from datetime import UTC, datetime

from tribal_assistant.core.agents.context import VillageContext

PREPARE_HOURS = 72
AXE_HOURS = 12


class Protection:
    @staticmethod
    def hours(ctx: VillageContext) -> float | None:
        until = (ctx.player or {}).get("protection_until")
        if not until:
            return None

        end = datetime.fromisoformat(str(until).replace("Z", "+00:00"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)

        return (end - datetime.now(UTC)).total_seconds() / 3600

    @classmethod
    def active(cls, ctx: VillageContext) -> bool:
        hours = cls.hours(ctx)
        return hours is not None and hours > 0

    @classmethod
    def ending(cls, ctx: VillageContext, within: float = PREPARE_HOURS) -> bool:
        hours = cls.hours(ctx)
        return hours is not None and 0 < hours <= within
