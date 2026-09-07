"""Keep Redis from serving canonicals that PostgreSQL has archived."""
import asyncio
import os

import asyncpg

from app.connections.redis_client import redis_client


async def main() -> None:
    dsn = os.getenv("DIRECT_DATABASE_URL") or os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
    if not dsn:
        print("[canonical-cache] No database DSN; skipping pending-canonical eviction")
        return
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        rows = await conn.fetch(
            'SELECT "topicSlug" FROM "CanonicalLesson" WHERE "pendingApproval" IS TRUE'
        )
        rewrite_ready = await conn.fetchval(
            '''SELECT count(*) FROM "StudentExperience"
                WHERE status='failed'
                  AND "errorMessage"='Rewrite requested 2026-09-07: terminology correction' '''
        )
    finally:
        await conn.close()
    for row in rows:
        await redis_client.delete(f'canonical:{row["topicSlug"]}')
    print(
        f"[canonical-cache] Evicted {len(rows)} pending canonical(s); "
        f"targeted rewrite rows ready: {rewrite_ready}"
    )


if __name__ == "__main__":
    asyncio.run(main())
