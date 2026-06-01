-- Manual migration to add ALU and ML tables without dropping existing data
-- This preserves the hippocampus_documents table (3634 rows of curriculum data)

-- Add AtomicUnit table
CREATE TABLE IF NOT EXISTS "AtomicUnit" (
    "id" TEXT NOT NULL,
    "unitSlug" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "lessonId" TEXT NOT NULL,
    "track" TEXT NOT NULL,
    "difficulty" TEXT NOT NULL DEFAULT 'DEVELOPING',
    "order" INTEGER NOT NULL DEFAULT 0,
    "estimatedCognitiveLoad" DOUBLE PRECISION NOT NULL DEFAULT 5.0,
    "targetModalities" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    "prerequisiteUnitSlugs" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    "temporalFrictionThresholdSecs" INTEGER NOT NULL DEFAULT 45,
    "maxIncorrectBeforeScaffold" INTEGER NOT NULL DEFAULT 1,
    "scaffoldComponent" TEXT NOT NULL DEFAULT 'FocusReset',
    "scaffoldProps" JSONB NOT NULL DEFAULT '{}',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "AtomicUnit_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "AtomicUnit_unitSlug_key" UNIQUE ("unitSlug")
);

-- Add indexes for AtomicUnit
CREATE INDEX IF NOT EXISTS "AtomicUnit_lessonId_idx" ON "AtomicUnit"("lessonId");
CREATE INDEX IF NOT EXISTS "AtomicUnit_track_idx" ON "AtomicUnit"("track");
CREATE INDEX IF NOT EXISTS "AtomicUnit_unitSlug_idx" ON "AtomicUnit"("unitSlug");

-- Add foreign key to CanonicalLesson
ALTER TABLE "AtomicUnit"
ADD CONSTRAINT "AtomicUnit_lessonId_fkey" FOREIGN KEY ("lessonId") REFERENCES "CanonicalLesson"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- Add assessed to XAPIVerb enum
-- PostgreSQL doesn't support ALTER TYPE ADD VALUE directly, so we recreate the enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'XAPIVerb') THEN
        CREATE TYPE "XAPIVerb" AS ENUM ('experienced', 'completed', 'attempted', 'passed', 'failed', 'scored', 'interacted', 'created', 'shared', 'observed', 'practiced', 'researched', 'sealed', 'focus_gap_detected', 'assessed');
    ELSE
        -- Add 'assessed' if it doesn't exist
        IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'assessed' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'XAPIVerb')) THEN
            ALTER TYPE "XAPIVerb" ADD VALUE 'assessed';
        END IF;
    END IF;
END $$;

-- Add ComponentInteractionLog table for ML training
CREATE TABLE IF NOT EXISTS "ComponentInteractionLog" (
    "id" TEXT NOT NULL,
    "studentId" TEXT NOT NULL,
    "componentId" TEXT NOT NULL,
    "componentType" TEXT NOT NULL,
    "lessonId" TEXT,
    "aluUnitSlug" TEXT,
    "track" TEXT NOT NULL,
    "interactionType" TEXT NOT NULL,
    "studentModality" TEXT,
    "componentModalities" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    "difficulty" TEXT NOT NULL DEFAULT 'DEVELOPING',
    "durationSecs" DOUBLE PRECISION,
    "completed" BOOLEAN NOT NULL DEFAULT false,
    "struggleCount" INTEGER NOT NULL DEFAULT 0,
    "hintsUsed" INTEGER NOT NULL DEFAULT 0,
    "masteryBefore" DOUBLE PRECISION,
    "masteryAfter" DOUBLE PRECISION,
    "context" JSONB NOT NULL DEFAULT '{}',
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ComponentInteractionLog_pkey" PRIMARY KEY ("id")
);

-- Add indexes for ComponentInteractionLog
CREATE INDEX IF NOT EXISTS "ComponentInteractionLog_studentId_idx" ON "ComponentInteractionLog"("studentId");
CREATE INDEX IF NOT EXISTS "ComponentInteractionLog_componentId_idx" ON "ComponentInteractionLog"("componentId");
CREATE INDEX IF NOT EXISTS "ComponentInteractionLog_track_idx" ON "ComponentInteractionLog"("track");
CREATE INDEX IF NOT EXISTS "ComponentInteractionLog_aluUnitSlug_idx" ON "ComponentInteractionLog"("aluUnitSlug");
CREATE INDEX IF NOT EXISTS "ComponentInteractionLog_timestamp_idx" ON "ComponentInteractionLog"("timestamp");
CREATE INDEX IF NOT EXISTS "ComponentInteractionLog_studentId_componentId_idx" ON "ComponentInteractionLog"("studentId", "componentId");
