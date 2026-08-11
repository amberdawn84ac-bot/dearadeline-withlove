"""Guarded one-time repair for the pre-existing initial eight-track schema."""

import asyncio
import os
import sys

import asyncpg


TARGET = "20260327192741_init_8_track_schema"
REQUIRED_ENUM_VALUES = {
    "UserRole": {"STUDENT", "PARENT", "ADMIN"},
    "Track": {
        "CREATION_SCIENCE", "HEALTH_NATUROPATHY", "HOMESTEADING",
        "GOVERNMENT_ECONOMICS", "JUSTICE_CHANGEMAKING", "DISCIPLESHIP",
        "TRUTH_HISTORY", "ENGLISH_LITERATURE",
    },
    "BlockType": {"TEXT", "PRIMARY_SOURCE", "LAB_MISSION", "RESEARCH_MISSION", "QUIZ"},
    "EvidenceVerdict": {"VERIFIED", "ARCHIVE_SILENT", "RESEARCH_MISSION"},
    "DifficultyLevel": {"EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"},
}
REQUIRED_COLUMNS = {
    "User": {"id", "name", "email", "role", "isHomestead", "gradeLevel", "createdAt", "updatedAt"},
    "Lesson": {"id", "title", "estimatedMinutes", "targetGrades", "createdAt", "updatedAt"},
    "LessonTrack": {"lessonId", "track"},
    "LessonBlock": {
        "id", "lessonId", "track", "blockType", "difficulty", "order", "title", "content",
        "isSilenced", "tags", "homesteadEnabled", "homesteadContent", "homesteadPractical", "createdAt",
    },
    "Evidence": {
        "id", "blockId", "sourceTitle", "sourceUrl", "similarityScore", "verdict", "chunk",
        "retrievedAt", "citationAuthor", "citationYear", "citationArchiveName",
    },
    "StudentLesson": {"studentId", "lessonId", "startedAt", "completedAt"},
}
REQUIRED_INDEXES = {
    "User_pkey", "User_email_key", "User_role_idx", "User_email_idx", "Lesson_pkey",
    "LessonTrack_pkey", "LessonBlock_pkey", "LessonBlock_lessonId_order_idx",
    "LessonBlock_blockType_idx", "Evidence_pkey", "Evidence_blockId_idx",
    "Evidence_verdict_idx", "Evidence_similarityScore_idx", "StudentLesson_pkey",
}
FOREIGN_KEYS = {
    "LessonTrack_lessonId_fkey": '''ALTER TABLE "LessonTrack" ADD CONSTRAINT "LessonTrack_lessonId_fkey"
        FOREIGN KEY ("lessonId") REFERENCES "Lesson"("id") ON DELETE CASCADE ON UPDATE CASCADE''',
    "LessonBlock_lessonId_fkey": '''ALTER TABLE "LessonBlock" ADD CONSTRAINT "LessonBlock_lessonId_fkey"
        FOREIGN KEY ("lessonId") REFERENCES "Lesson"("id") ON DELETE CASCADE ON UPDATE CASCADE''',
    "Evidence_blockId_fkey": '''ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_blockId_fkey"
        FOREIGN KEY ("blockId") REFERENCES "LessonBlock"("id") ON DELETE CASCADE ON UPDATE CASCADE''',
    "StudentLesson_studentId_fkey": '''ALTER TABLE "StudentLesson" ADD CONSTRAINT "StudentLesson_studentId_fkey"
        FOREIGN KEY ("studentId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE''',
    "StudentLesson_lessonId_fkey": '''ALTER TABLE "StudentLesson" ADD CONSTRAINT "StudentLesson_lessonId_fkey"
        FOREIGN KEY ("lessonId") REFERENCES "Lesson"("id") ON DELETE RESTRICT ON UPDATE CASCADE''',
}


def fail(message: str) -> None:
    raise RuntimeError(f"[migration-repair] refused: {message}")


async def main() -> int:
    dsn = os.getenv("DIRECT_DATABASE_URL") or os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
    if not dsn:
        fail("no database DSN")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        row = await conn.fetchrow(
            '''SELECT finished_at, rolled_back_at, applied_steps_count, logs
               FROM "_prisma_migrations" WHERE migration_name = $1''',
            TARGET,
        )
        if row is None:
            fail("target migration record is missing")
        if row["finished_at"] is not None:
            print("[migration-repair] initial migration already healthy")
            return 0
        if row["rolled_back_at"] is not None:
            fail("target migration is recorded as rolled back")
        if row["applied_steps_count"] != 0 or 'type "UserRole" already exists' not in (row["logs"] or ""):
            fail("failure signature differs from the inspected zero-step enum collision")

        for enum_name, required in REQUIRED_ENUM_VALUES.items():
            values = await conn.fetch(
                '''SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
                   JOIN pg_namespace n ON n.oid = t.typnamespace
                   WHERE n.nspname = 'public' AND t.typname = $1''',
                enum_name,
            )
            actual = {record["enumlabel"] for record in values}
            if not required.issubset(actual):
                fail(f"enum {enum_name} is missing {sorted(required - actual)}")

        for table, required in REQUIRED_COLUMNS.items():
            actual = set(await conn.fetchval(
                '''SELECT coalesce(array_agg(column_name), ARRAY[]::text[])
                   FROM information_schema.columns WHERE table_schema = 'public' AND table_name = $1''',
                table,
            ))
            if not required.issubset(actual):
                fail(f"table {table} is missing columns {sorted(required - actual)}")

        actual_indexes = set(await conn.fetchval(
            '''SELECT coalesce(array_agg(indexname), ARRAY[]::text[])
               FROM pg_indexes WHERE schemaname = 'public' ''',
        ))
        if not REQUIRED_INDEXES.issubset(actual_indexes):
            fail(f"missing indexes {sorted(REQUIRED_INDEXES - actual_indexes)}")

        async with conn.transaction():
            existing = set(await conn.fetchval(
                '''SELECT coalesce(array_agg(constraint_name), ARRAY[]::text[])
                   FROM information_schema.table_constraints WHERE table_schema = 'public' ''',
            ))
            for name, statement in FOREIGN_KEYS.items():
                if name not in existing:
                    await conn.execute(statement)
                    print(f"[migration-repair] added {name}")
        print("[migration-repair] schema verified; Prisma resolution required")
        return 42
    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
