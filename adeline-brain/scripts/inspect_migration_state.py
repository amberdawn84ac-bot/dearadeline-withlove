"""Read-only production diagnostics for complete Prisma migration drift."""

import asyncio
import json
import os

import asyncpg


def dump(label, rows):
    print(f"[migration-inspector] {label}=" + json.dumps([dict(row) for row in rows], default=str))


async def main() -> None:
    dsn = os.getenv("DIRECT_DATABASE_URL") or os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
    if not dsn:
        print("[migration-inspector] no database DSN; skipped")
        return

    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        dump("migrations", await conn.fetch(
            '''SELECT migration_name, started_at, finished_at, rolled_back_at,
                      applied_steps_count, logs
               FROM "_prisma_migrations"
               ORDER BY started_at, migration_name'''
        ))
        dump("enums", await conn.fetch(
            '''SELECT t.typname AS name,
                      array_agg(e.enumlabel ORDER BY e.enumsortorder) AS values
               FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
               JOIN pg_namespace n ON n.oid = t.typnamespace
               WHERE n.nspname = 'public'
               GROUP BY t.typname ORDER BY t.typname'''
        ))
        dump("columns", await conn.fetch(
            '''SELECT table_name, column_name, data_type, udt_name, is_nullable,
                      column_default
               FROM information_schema.columns
               WHERE table_schema = 'public'
               ORDER BY table_name, ordinal_position'''
        ))
        dump("constraints", await conn.fetch(
            '''SELECT tc.table_name, tc.constraint_name, tc.constraint_type
               FROM information_schema.table_constraints tc
               WHERE tc.table_schema = 'public'
               ORDER BY tc.table_name, tc.constraint_name'''
        ))
        dump("indexes", await conn.fetch(
            '''SELECT tablename, indexname, indexdef FROM pg_indexes
               WHERE schemaname = 'public' ORDER BY tablename, indexname'''
        ))
        dump("extensions", await conn.fetch(
            '''SELECT extname, extversion FROM pg_extension ORDER BY extname'''
        ))
        dump("policies", await conn.fetch(
            '''SELECT tablename, policyname, permissive, roles, cmd, qual, with_check
               FROM pg_policies WHERE schemaname = 'public'
               ORDER BY tablename, policyname'''
        ))
        tables = await conn.fetch(
            '''SELECT table_name FROM information_schema.tables
               WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
               ORDER BY table_name'''
        )
        counts = {}
        for row in tables:
            table = row["table_name"]
            quoted = table.replace('"', '""')
            counts[table] = await conn.fetchval(f'SELECT count(*) FROM "{quoted}"')
        print("[migration-inspector] row_counts=" + json.dumps(counts, sort_keys=True))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
