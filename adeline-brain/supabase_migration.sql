-- OAS Standard Mastery Migration for Supabase SQL Editor
-- Run this in Supabase Dashboard → SQL Editor → New query

-- 1. Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create OASProficiencyLevel enum type
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'oasproficiencylevel') THEN
        CREATE TYPE "OASProficiencyLevel" AS ENUM ('DEVELOPING', 'APPROACHING', 'UNDERSTANDING', 'EXTENDING');
    END IF;
END$$;

-- 3. Create StandardMastery table
CREATE TABLE IF NOT EXISTS "StandardMastery" (
    "id" TEXT NOT NULL DEFAULT gen_random_uuid(),
    "studentId" TEXT NOT NULL,
    "standardId" TEXT NOT NULL,
    "subject" TEXT NOT NULL,
    "grade" INTEGER NOT NULL,
    "proficiency" "OASProficiencyLevel" NOT NULL DEFAULT 'DEVELOPING',
    "evidenceCount" INTEGER NOT NULL DEFAULT 0,
    "lastEvidenceAt" TIMESTAMP(3),
    "lastAssessedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "StandardMastery_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "StandardMastery_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "StandardMastery_unique_student_standard" UNIQUE ("studentId", "standardId")
);

-- 4. Create indexes for StandardMastery
CREATE INDEX IF NOT EXISTS "StandardMastery_studentId_idx" ON "StandardMastery"("studentId");
CREATE INDEX IF NOT EXISTS "StandardMastery_standardId_idx" ON "StandardMastery"("standardId");
CREATE INDEX IF NOT EXISTS "StandardMastery_subject_grade_idx" ON "StandardMastery"("subject", "grade");
CREATE INDEX IF NOT EXISTS "StandardMastery_proficiency_idx" ON "StandardMastery"("proficiency");

-- 5. Create OASStandard reference table
CREATE TABLE IF NOT EXISTS "OASStandard" (
    "id" TEXT NOT NULL DEFAULT gen_random_uuid(),
    "code" TEXT NOT NULL UNIQUE,
    "subject" TEXT NOT NULL,
    "grade" INTEGER NOT NULL,
    "gradeBand" TEXT NOT NULL,
    "strand" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "track" TEXT NOT NULL,
    "lessonHook" TEXT,
    "homesteadAdaptation" TEXT,
    "difficulty" TEXT NOT NULL DEFAULT 'EMERGING',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS "OASStandard_code_idx" ON "OASStandard"("code");
CREATE INDEX IF NOT EXISTS "OASStandard_subject_grade_idx" ON "OASStandard"("subject", "grade");
CREATE INDEX IF NOT EXISTS "OASStandard_track_idx" ON "OASStandard"("track");

-- 6. Create materialized view for fast graduation readiness queries
DROP MATERIALIZED VIEW IF EXISTS graduation_readiness_cache;
CREATE MATERIALIZED VIEW graduation_readiness_cache AS
SELECT 
    "studentId" as student_id,
    subject,
    COUNT(*) as total_standards,
    COUNT(*) FILTER (WHERE proficiency IN ('UNDERSTANDING', 'EXTENDING')) as mastered_count,
    ROUND(
        COUNT(*) FILTER (WHERE proficiency IN ('UNDERSTANDING', 'EXTENDING')) * 100.0 / NULLIF(COUNT(*), 0), 
        2
    ) as saturation_pct,
    MAX("lastAssessedAt") as last_updated
FROM "StandardMastery"
GROUP BY "studentId", subject;

-- 7. Create indexes on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_grad_cache_student_subject ON graduation_readiness_cache(student_id, subject);
CREATE INDEX IF NOT EXISTS idx_grad_cache_student ON graduation_readiness_cache(student_id);
CREATE INDEX IF NOT EXISTS idx_grad_cache_saturation ON graduation_readiness_cache(saturation_pct);

-- 8. Add comment explaining refresh strategy
COMMENT ON MATERIALIZED VIEW graduation_readiness_cache IS 
'Cached OAS standards mastery data for fast graduation reports.
Refresh: REFRESH MATERIALIZED VIEW CONCURRENTLY graduation_readiness_cache;
Recommended: Run every 5 minutes or on-demand via StandardsMapper.';

-- 9. Verify setup
SELECT 'Migration complete!' as status;
SELECT COUNT(*) as standard_mastery_tables_created FROM information_schema.tables WHERE table_name = 'StandardMastery';
