"""Real PostgreSQL reset check; isolated schema, never the application's tables."""

import os
from pathlib import Path
from uuid import uuid4
import asyncpg
import pytest


@pytest.mark.asyncio
async def test_reset_removes_old_teaching_and_preserves_new_classrooms_and_learner_records():
    dsn = os.environ.get("POSTGRES_DSN")
    if not dsn:
        pytest.skip("Requires an isolated PostgreSQL test database")
    conn = await asyncpg.connect(dsn)
    schema = "classroom_reset_" + uuid4().hex
    root = Path(__file__).resolve().parents[1]
    try:
        async with conn.transaction():
            await conn.execute(f'CREATE SCHEMA "{schema}"')
            await conn.execute(f'SET LOCAL search_path TO "{schema}"')
            await conn.execute(
                (root / "tests/fixtures/classroom_reset.sql").read_text()
            )
            migration = (
                root / "prisma/migrations/20261017_reset_legacy_lessons/migration.sql"
            ).read_text()
            await conn.execute(migration)
            await conn.execute(migration)
            assert (
                await conn.fetchval(
                    'SELECT "blocksJson"::text FROM "CanonicalLesson" WHERE id=\'old\''
                )
                == "[]"
            )
            assert (
                await conn.fetchval(
                    'SELECT "pendingApproval" FROM "CanonicalLesson" WHERE id=\'new\''
                )
                is False
            )
            assert (
                await conn.fetchval(
                    "SELECT status FROM \"StudentExperience\" WHERE id='old'"
                )
                == "failed"
            )
            assert (
                await conn.fetchval(
                    "SELECT status FROM \"StudentExperience\" WHERE id='new'"
                )
                == "ready"
            )
            assert await conn.fetchval('SELECT count(*) FROM "DailyPlan"') == 0
            for table in ("User", "EvidenceAttempt", "StudentCharacter"):
                assert await conn.fetchval(f'SELECT count(*) FROM "{table}"') == 1
            await conn.execute(f'DROP SCHEMA "{schema}" CASCADE')
    finally:
        await conn.close()
