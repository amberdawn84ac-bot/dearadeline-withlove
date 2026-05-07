"""
ARQ WorkerSettings — runs as a separate Railway service.

Start command: arq app.worker.WorkerSettings

Shares the same Docker image as the web service.
Initializes the same DB connections the orchestrator requires.
"""
import logging
import os
from arq import cron
from arq.connections import RedisSettings

from app.jobs.warmup_jobs import warmup_canonical_cache

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Validate that REDIS_URL is a TCP DSN — ARQ cannot use Upstash HTTP REST protocol
# If only UPSTASH_REDIS_REST_URL is set, ARQ will silently fail. Both must be configured:
#   UPSTASH_REDIS_REST_URL — for canonical_store, session cache (HTTP REST)
#   REDIS_URL              — for ARQ task queue (TCP connection)
if _REDIS_URL.startswith("https://") or _REDIS_URL.startswith("http://"):
    raise ValueError(
        f"[ARQ Worker] REDIS_URL must be a redis:// TCP DSN, not an HTTP URL: {_REDIS_URL}\n"
        "ARQ requires a real Redis TCP connection. Set REDIS_URL to your Railway Redis URL.\n"
        "UPSTASH_REDIS_REST_URL is used separately for canonical_store and session cache."
    )


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
    # NOTE: generate_lesson_job removed — lessons now use streaming via /lesson/stream
    functions = [warmup_canonical_cache]
    cron_jobs = [
        cron(warmup_canonical_cache, hour=2, minute=0),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(_REDIS_URL)
    max_jobs = 4
    job_timeout = 120          # seconds — matches Gunicorn timeout
    keep_result = 3600         # keep results in Redis for 1 hour
    keep_result_forever = False
    retry_jobs = False         # don't retry failed lessons — return error to user
