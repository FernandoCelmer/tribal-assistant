"""APScheduler singleton + job registration."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.jobs import register_jobs

scheduler = AsyncIOScheduler()
register_jobs(scheduler)
