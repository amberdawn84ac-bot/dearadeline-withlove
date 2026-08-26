"""Scheduled corpus collection and canonical-library replenishment."""
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.jobs.seed_thin_tracks import seed_thin_tracks
from app.jobs.canonical_seeding import (
    canonical_seeding_enabled,
    scheduled_canonical_replenishment,
)

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler = None


async def startup_seed_scheduler():
    """
    Initialize and start the seed scheduler.

    Runs nightly at 3 AM UTC to grow Hippocampus coverage across
    GOVERNMENT_ECONOMICS, APPLIED_MATHEMATICS, CREATIVE_ECONOMY,
    TRUTH_HISTORY, and JUSTICE_CHANGEMAKING via the free DuckDuckGo-backed
    Researcher fallback (see app/jobs/seed_thin_tracks.py).
    Called on FastAPI startup event.
    """
    global _scheduler

    if _scheduler is None:
        _scheduler = AsyncIOScheduler()

        if canonical_seeding_enabled():
            day = os.getenv("CANONICAL_SEED_DAY_OF_WEEK", "sun").strip().lower()
            hour = int(os.getenv("CANONICAL_SEED_HOUR", "2"))
            minute = int(os.getenv("CANONICAL_SEED_MINUTE", "0"))
            timezone = os.getenv("CANONICAL_SEED_TIMEZONE", "America/Chicago").strip()
            _scheduler.add_job(
                scheduled_canonical_replenishment,
                "cron",
                day_of_week=day,
                hour=hour,
                minute=minute,
                timezone=timezone,
                id="replenish_canonical_library_weekly",
                name="Pre-author Canonical Lessons (Weekly)",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=60 * 60 * 6,
            )

        # Gov/Math/Creative + History/Justice primary sources: 3:00 AM UTC every day
        _scheduler.add_job(
            seed_thin_tracks,
            'cron',
            hour=3,
            minute=0,
            timezone='UTC',
            id='seed_thin_tracks_nightly',
            name='Seed Thin Tracks + History/Justice Primary Sources (Nightly)',
            max_instances=1,
        )

        _scheduler.start()
        logger.info("[Scheduler] Started APScheduler with nightly seeding jobs:")
        logger.info("  - Gov/Math/Creative + History/Justice primary sources: 03:00 UTC")
        if canonical_seeding_enabled():
            logger.info(
                "  - Canonical lessons: %s %02d:%02d %s (batch=%s)",
                os.getenv("CANONICAL_SEED_DAY_OF_WEEK", "sun"),
                int(os.getenv("CANONICAL_SEED_HOUR", "2")),
                int(os.getenv("CANONICAL_SEED_MINUTE", "0")),
                os.getenv("CANONICAL_SEED_TIMEZONE", "America/Chicago"),
                os.getenv("CANONICAL_SEED_BATCH_SIZE", "6"),
            )
        else:
            logger.info("  - Canonical lessons: disabled (CANONICAL_SEEDING_ENABLED=false)")


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
