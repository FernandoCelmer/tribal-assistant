"""APScheduler singleton + job registration."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tribal_assistant.core.scheduler.jobs import register_jobs

scheduler = AsyncIOScheduler()
register_jobs(scheduler)
