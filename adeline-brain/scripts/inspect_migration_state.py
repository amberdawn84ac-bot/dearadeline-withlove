"""Read-only production migration diagnostics for the failed initial schema migration."""

import asyncio
import json
import os

import asyncpg


TARGET = "20260327192741_init_8_track_schema"
CORE_TABLES = ("User", "Lesson", "LessonTrack", "LessonBlock", "Evidence", "StudentLesson")
CORE_ENUMS = ("UserRole", "Track", "BlockType", "EvidenceVerdict", "DifficultyLevel")


async def main() -> None:
    dsn = os.getenv("DIRECT_DATABASE_URL") or os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
    if not dsn:
        print("[migration-inspector] no database DSN; skipped")
        return

    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        migration = await conn.fetchrow(
            '''SELECT migration_name, started_at, finished_at, rolled_back_at,
                      applied_steps_count, logs
               FROM "_prisma_migrations" WHERE migration_name = $1''',
            TARGET,
        )
        print("[migration-inspector] migration=" + json.dumps(dict(migration) if migration else None, default=str))

        enums = await conn.fetch(
            '''SELECT t.typname AS name,
                      array_agg(e.enumlabel ORDER BY e.enumsortorder) AS values
               FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
               JOIN pg_namespace n ON n.oid = t.typnamespace
               WHERE n.nspname = 'public' AND t.typname = ANY($1::text[])
               GROUP BY t.typname ORDER BY t.typname''',
            list(CORE_ENUMS),
        )
        print("[migration-inspector] enums=" + json.dumps([dict(row) for row in enums], default=str))

        tables = await conn.fetch(
            '''SELECT table_name FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = ANY($1::text[])
               ORDER BY table_name''',
            list(CORE_TABLES),
        )
        print("[migration-inspector] tables=" + json.dumps([row["table_name"] for row in tables]))

        constraints = await conn.fetch(
            '''SELECT tc.table_name, tc.constraint_name, tc.constraint_type
               FROM information_schema.table_constraints tc
               WHERE tc.table_schema = 'public' AND tc.table_name = ANY($1::text[])
               ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name''',
            list(CORE_TABLES),
        )
        print("[migration-inspector] constraints=" + json.dumps([dict(row) for row in constraints]))

        indexes = await conn.fetch(
            '''SELECT tablename, indexname, indexdef FROM pg_indexes
               WHERE schemaname = 'public' AND tablename = ANY($1::text[])
               ORDER BY tablename, indexname''',
            list(CORE_TABLES),
        )
        print("[migration-inspector] indexes=" + json.dumps([dict(row) for row in indexes]))

        counts = {}
        for table in CORE_TABLES:
            exists = await conn.fetchval("SELECT to_regclass($1)", f'public."{table}"')
            if exists:
                counts[table] = await conn.fetchval(f'SELECT count(*) FROM "{table}"')
        print("[migration-inspector] row_counts=" + json.dumps(counts))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
