-- Migration: Add OAS Standard Mastery tracking and graduation readiness caching
-- Created: 2025-01-12

-- Create OASProficiencyLevel enum
CREATE TYPE "OASProficiencyLevel" AS ENUM ('DEVELOPING', 'APPROACHING', 'UNDERSTANDING', 'EXTENDING');

-- Create StandardMastery table for tracking OAS proficiency per student/standard
CREATE TABLE "StandardMastery" (
    "id" TEXT NOT NULL,
    "studentId" TEXT NOT NULL,
    "standardId" TEXT NOT NULL,
    "subject" TEXT NOT NULL,
    "grade" INTEGER NOT NULL,
    "proficiency" "OASProficiencyLevel" NOT NULL DEFAULT 'DEVELOPING',
    "evidenceCount" INTEGER NOT NULL DEFAULT 0,
    "lastEvidenceAt" TIMESTAMP(3),
    "lastAssessedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "StandardMastery_pkey" PRIMARY KEY ("id")
);

-- Create unique index on studentId + standardId
CREATE UNIQUE INDEX "StandardMastery_studentId_standardId_key" ON "StandardMastery"("studentId", "standardId");

-- Create indexes for efficient queries
CREATE INDEX "StandardMastery_studentId_idx" ON "StandardMastery"("studentId");
CREATE INDEX "StandardMastery_standardId_idx" ON "StandardMastery"("standardId");
CREATE INDEX "StandardMastery_subject_grade_idx" ON "StandardMastery"("subject", "grade");
CREATE INDEX "StandardMastery_proficiency_idx" ON "StandardMastery"("proficiency");

-- Add foreign key to User table
ALTER TABLE "StandardMastery" ADD CONSTRAINT "StandardMastery_studentId_fkey" 
    FOREIGN KEY ("studentId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- Create OASStandard reference table (populated from Neo4j seed)
CREATE TABLE "OASStandard" (
    "id" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "subject" TEXT NOT NULL,
    "grade" INTEGER NOT NULL,
    "gradeBand" TEXT NOT NULL,
    "strand" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "track" TEXT NOT NULL,
    "lessonHook" TEXT,
    "homesteadAdaptation" TEXT,
    "difficulty" TEXT NOT NULL DEFAULT 'EMERGING',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "OASStandard_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "OASStandard_code_key" ON "OASStandard"("code");
CREATE INDEX "OASStandard_subject_grade_idx" ON "OASStandard"("subject", "grade");
CREATE INDEX "OASStandard_track_idx" ON "OASStandard"("track");

-- Create materialized view for fast graduation readiness queries
CREATE MATERIALIZED VIEW graduation_readiness_cache AS
SELECT 
    "studentId" as student_id,
    subject,
    COUNT(*) as total_standards,
    COUNT(*) FILTER (WHERE proficiency IN ('UNDERSTANDING', 'EXTENDING')) as mastered_count,
    ROUND(
        COUNT(*) FILTER (WHERE proficiency IN ('UNDERSTANDING', 'EXTENDING')) * 100.0 / COUNT(*), 
        2
    ) as saturation_pct,
    MAX("lastAssessedAt") as last_updated
FROM "StandardMastery"
GROUP BY "studentId", subject;

-- Create index on materialized view for fast lookups
CREATE UNIQUE INDEX idx_grad_cache_student_subject ON graduation_readiness_cache(student_id, subject);
CREATE INDEX idx_grad_cache_student ON graduation_readiness_cache(student_id);
CREATE INDEX idx_grad_cache_saturation ON graduation_readiness_cache(saturation_pct);

-- Create function to refresh cache on StandardMastery changes
CREATE OR REPLACE FUNCTION refresh_graduation_cache()
RETURNS TRIGGER AS $$
BEGIN
    -- Note: In production, use a scheduled job or trigger-based incremental update
    -- This is a placeholder for the refresh strategy
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to invalidate cache on mastery updates
CREATE TRIGGER refresh_cache_on_mastery
    AFTER INSERT OR UPDATE OR DELETE ON "StandardMastery"
    FOR EACH ROW
    EXECUTE FUNCTION refresh_graduation_cache();

-- Add comment explaining the refresh strategy
COMMENT ON MATERIALIZED VIEW graduation_readiness_cache IS 
'Cached OAS standards mastery data for fast graduation reports.
Refresh strategy: Call REFRESH MATERIALIZED VIEW CONCURRENTLY graduation_readiness_cache;
Recommended: Every 5 minutes or on-demand via StandardsMapper._invalidate_cache()';
