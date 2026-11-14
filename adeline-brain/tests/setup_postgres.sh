#!/usr/bin/env bash
# Bootstrap an empty disposable PostgreSQL database with the schema used by CI.
# Supabase roles and the SQLAlchemy-owned journal are not in the Prisma baseline.
set -euo pipefail
psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
END $$;
CREATE TABLE student_journal (
    student_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    track TEXT NOT NULL,
    completed_blocks INTEGER NOT NULL DEFAULT 0,
    sources_json TEXT,
    plan_item_id TEXT,
    sealed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (student_id, lesson_id)
);
SQL
psql -v ON_ERROR_STOP=1 -f prisma/migrations/apply_all.sql
psql -v ON_ERROR_STOP=1 -f supabase_migration.sql
for migration in \
    20260602_add_coppa_verification \
    20260817_consolidate_curriculum_graph_in_postgres \
    20260823_parent_privacy_and_scale \
    20260826_add_curriculum_relation_provenance \
    20260829_place_all_standards_in_progressions \
    20260904_add_space_credit_tracking \
    20260905_add_experience_failure_count \
    20260905_replace_family_investigation_override_with_queue \
    20261003_unified_curriculum \
    20261019_learning_loop; do
    psql -v ON_ERROR_STOP=1 -f "prisma/migrations/$migration/migration.sql"
done
