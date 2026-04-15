"""
ARQ WorkerSettings — runs as a separate Railway service.

Start command: arq app.worker.WorkerSettings

Shares the same Docker image as the web service.
Initializes the same DB connections the orchestrator requires.
"""
import logging
import os
from arq.connections import RedisSettings

from app.jobs.lesson_jobs import generate_lesson_job

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def startup(ctx: dict) -> None:
    """Initialize connections needed by lesson generation jobs."""
    from app.connections.pgvector_client import hippocampus
    from app.connections.neo4j_client import neo4j_client

    try:
        await hippocampus.connect()
        logger.info("[ARQ Worker] Hippocampus connected")
    except Exception as e:
        logger.warning(f"[ARQ Worker] Hippocampus unavailable: {e}")

    try:
        await neo4j_client.connect()
        logger.info("[ARQ Worker] Neo4j connected")
    except Exception as e:
        logger.warning(f"[ARQ Worker] Neo4j unavailable (ZPD degraded): {e}")


async def shutdown(ctx: dict) -> None:
    """Clean up connections on worker shutdown."""
    from app.connections.pgvector_client import hippocampus
    from app.connections.neo4j_client import neo4j_client

    try:
        await hippocampus.disconnect()
    except Exception:
        pass
    try:
        await neo4j_client.close()
    except Exception:
        pass


class WorkerSettings:
    # ARQ requires actual function objects, not string paths
    functions = [generate_lesson_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(_REDIS_URL)
    max_jobs = 4
    job_timeout = 120          # seconds — matches Gunicorn timeout
    keep_result = 3600         # keep results in Redis for 1 hour
    keep_result_forever = False
    retry_jobs = False         # don't retry failed lessons — return error to user
