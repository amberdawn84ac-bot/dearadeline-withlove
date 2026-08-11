"""Guardedly reconcile historical Prisma migrations with a pre-existing production schema."""

import argparse
import asyncio
import os
import sys

import asyncpg


MIGRATIONS = [
    "20260327_add_invite_codes",
    "20260329_add_learning_records",
    "20260329_add_tracks_9_10",
    "20260402_add_hippocampus_document",
    "20260403_add_onboarding_fields",
    "20260404_add_books_table",
    "20260404_add_reading_session",
    "20260409_add_reading_recommendations_log",
    "20260412_add_canonical_lessons",
    "20260414_canonical_approval",
    "20260414_canonical_auditability",
    "20260521_add_subscription",
    "20260521_canonical_topicslug_unique",
    "20260521_fix_user_updatedat_default",
    "20260523_add_book_table",
    "20260523_backfill_student_subscriptions",
    "20260525_fix_hippocampus_dedup",
    "20260804_add_student_mobile_fields",
    "20260805_add_town_player_systems",
    "20260806_add_storm_fields",
    "20260806_add_town_id_index",
]
TABLE_COLUMNS = {
    "InviteCode": {"id", "code", "isUsed", "claimedByEmail", "createdAt"},
    "LearningRecord": {"id", "studentId", "lessonId", "verb", "track", "statementJson", "timestamp"},
    "TranscriptEntry": {"id", "studentId", "lessonId", "track", "creditType", "completedAt"},
    "SpacedRepetitionCard": {"id", "studentId", "conceptId", "track", "dueAt"},
    "HippocampusDocument": {"id", "source_url", "source_title", "chunk", "embedding", "track"},
    "User": {
        "mathLevel", "elaLevel", "scienceLevel", "historyLevel", "interests", "learningStyle",
        "pacingMultiplier", "state", "targetGraduationYear", "onboardingComplete", "xp",
        "adeCoins", "avatarData", "seasonPass", "username", "pinHash", "linkCode", "townId",
        "reputation",
    },
    "Book": {
        "id", "title", "author", "description", "track", "gradeBand", "lexileLevel",
        "coverImageUrl", "sourceUrl", "isbn", "totalPages", "source_url", "lexile_level",
        "grade_band", "embedding",
    },
    "ReadingSession": {
        "id", "studentId", "bookId", "status", "startedAt", "completedAt", "pagesRead",
        "totalPages", "currentLocation", "updatedAt",
    },
    "ReadingRecommendationsLog": {
        "id", "studentId", "recommendedBookIds", "adaptiveLexileMin", "adaptiveLexileMax",
        "confidenceScore", "recommendationDate",
    },
    "CanonicalLesson": {
        "id", "topicSlug", "topic", "track", "title", "blocksJson", "oasStandards",
        "pendingApproval", "needsReviewReason", "lastApprovedAt", "approvedBy",
    },
    "Subscription": {"id", "userId", "tier", "status", "createdAt", "updatedAt"},
    "Town": {"id", "name", "joinCode", "treasury", "stormPrepCount", "lastStormCycleEvaluated"},
    "TownBuilding": {"id", "townId", "buildingKey"},
    "Item": {"id", "name", "type"},
    "TownSupply": {"id", "townId", "itemId", "quantity"},
    "PlayerInventory": {"id", "studentId", "itemId", "quantity"},
    "Achievement": {"id", "key", "name"},
    "PlayerAchievement": {"id", "studentId", "achievementId", "earnedAt"},
}
REQUIRED_INDEXES = {
    "InviteCode_code_key", "InviteCode_code_idx",
    "LearningRecord_studentId_idx", "TranscriptEntry_studentId_lessonId_key",
    "SpacedRepetitionCard_studentId_conceptId_key",
    "HippocampusDocument_source_url_track_key", "HippocampusDocument_embedding_idx",
    "User_onboardingComplete_idx", "Book_embedding_idx", "ReadingSession_studentId_bookId_key",
    "ReadingRecommendationsLog_studentId_idx", "CanonicalLesson_track_idx",
    "CanonicalLesson_pending_idx", "Subscription_userId_key",
    "hippocampus_document_source_url_chunk_key", "User_username_key", "User_linkCode_key", "User_townId_idx",
}
REQUIRED_ENUMS = {
    "Track": {"APPLIED_MATHEMATICS", "CREATIVE_ECONOMY"},
    "BlockType": {"NARRATIVE"},
    "XAPIVerb": {"experienced", "sealed"},
    "CreditType": {"CORE", "ELECTIVE", "PHYSICAL_ED", "FINE_ARTS", "HOMESTEAD"},
    "GradeLetter": {"A", "PASS", "FAIL", "INCOMPLETE"},
    "AgentName": {"HistorianAgent", "ScienceAgent", "DiscipleshipAgent", "RegistrarAgent"},
}
FOCUS_ENUM_VALUES = {
    "BlockType": {
        "SIMULATION", "VIDEO", "TEXT_DEEP", "REAL_WORLD_APP", "CORRECTIVE_OVERLAY", "CONCEPT_MAP",
    },
    "XAPIVerb": {"focus_gap_detected"},
}


def fail(message):
    raise RuntimeError(f"[migration-history] refused: {message}")


async def enum_values(conn, name):
    rows = await conn.fetch(
        """SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
           JOIN pg_namespace n ON n.oid = t.typnamespace
           WHERE n.nspname = 'public' AND t.typname = $1""",
        name,
    )
    return {row["enumlabel"] for row in rows}


async def verify(conn):
    for table, required in TABLE_COLUMNS.items():
        columns = set(await conn.fetchval(
            """SELECT coalesce(array_agg(column_name), ARRAY[]::text[])
               FROM information_schema.columns
               WHERE table_schema = 'public' AND table_name = $1""",
            table,
        ))
        if not required.issubset(columns):
            fail(f"{table} is missing columns {sorted(required - columns)}")

    indexes = set(await conn.fetchval(
        """SELECT coalesce(array_agg(indexname), ARRAY[]::text[])
           FROM pg_indexes WHERE schemaname = 'public'"""
    ))
    if not REQUIRED_INDEXES.issubset(indexes):
        fail(f"missing indexes {sorted(REQUIRED_INDEXES - indexes)}")

    constraints = set(await conn.fetchval(
        """SELECT coalesce(array_agg(constraint_name), ARRAY[]::text[])
           FROM information_schema.table_constraints WHERE table_schema = 'public'"""
    ))
    for name in {"InviteCode_pkey", "CanonicalLesson_topicSlug_key"}:
        if name not in constraints:
            fail(f"missing constraint {name}")

    for name, required in REQUIRED_ENUMS.items():
        actual = await enum_values(conn, name)
        if not required.issubset(actual):
            fail(f"enum {name} is missing {sorted(required - actual)}")

    if not await conn.fetchval("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"):
        fail("vector extension is missing")
    if not await conn.fetchval(
        """SELECT column_default IS NOT NULL FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = 'User' AND column_name = 'updatedAt'"""
    ):
        fail('User.updatedAt default is missing')
    missing_subscriptions = await conn.fetchval(
        """SELECT count(*) FROM "User" u
           WHERE u."onboardingComplete" = true
             AND NOT EXISTS (SELECT 1 FROM "Subscription" s WHERE s."userId" = u.id)"""
    )
    if missing_subscriptions:
        fail(f"{missing_subscriptions} onboarded users are missing subscription backfill")


async def repair_focus_enums(conn):
    for enum_name, required in FOCUS_ENUM_VALUES.items():
        actual = await enum_values(conn, enum_name)
        for value in sorted(required - actual):
            safe_value = value.replace("'", "''")
            safe_enum = enum_name.replace('"', '""')
            await conn.execute(f"""ALTER TYPE "{safe_enum}" ADD VALUE '{safe_value}'""")
            print(f"[migration-history] added {enum_name}.{value}", file=sys.stderr)


async def main(list_only):
    dsn = os.getenv("DIRECT_DATABASE_URL") or os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
    if not dsn:
        fail("no database DSN")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        await verify(conn)
        await repair_focus_enums(conn)
        healthy = {
            row["migration_name"]
            for row in await conn.fetch(
                """SELECT DISTINCT migration_name FROM "_prisma_migrations"
                   WHERE finished_at IS NOT NULL AND rolled_back_at IS NULL"""
            )
        }
        pending = [name for name in MIGRATIONS if name not in healthy]
        if list_only:
            print(" ".join(pending))
        else:
            print(f"[migration-history] verified {len(MIGRATIONS)} historical migrations; "
                  f"{len(pending)} require Prisma resolution", file=sys.stderr)
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    try:
        sys.exit(asyncio.run(main(args.list)))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
