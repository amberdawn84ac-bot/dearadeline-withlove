"""Scheduled jobs for Hippocampus seeding."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scripts.seed_declassified_documents import seed_all_declassified_documents

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler = None


async def startup_seed_scheduler():
    """
    Initialize and start the seed scheduler.

    Runs nightly at 2 AM UTC to seed Hippocampus with declassified documents.
    Called on FastAPI startup event.
    """
    global _scheduler

    if _scheduler is None:
        _scheduler = AsyncIOScheduler()

        # Register nightly seeding job: 2 AM UTC every day
        _scheduler.add_job(
            seed_all_declassified_documents,
            'cron',
            hour=2,
            minute=0,
            timezone='UTC',
            id='seed_declassified_documents_nightly',
            name='Seed Declassified Documents (Nightly)',
            max_instances=1,  # Prevent concurrent execution
        )

        _scheduler.start()
        logger.info("[Scheduler] Started APScheduler with nightly declassified document seeding at 02:00 UTC")


async def shutdown_seed_scheduler():
    """
    Shutdown the scheduler gracefully.
    Called on FastAPI shutdown event.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("[Scheduler] Shutdown APScheduler")


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    return _scheduler
