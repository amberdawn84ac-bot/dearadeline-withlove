CREATE TABLE IF NOT EXISTS "StudentExperience" (
  id              TEXT NOT NULL,
  "studentId"     TEXT NOT NULL,
  "planItemId"    TEXT NOT NULL,
  "canonicalSlug" TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'not_started',
  title           TEXT,
  track           TEXT,
  "blocksJson"    JSONB NOT NULL DEFAULT '[]'::jsonb,
  "metadataJson"  JSONB NOT NULL DEFAULT '{}'::jsonb,
  "errorMessage"  TEXT,
  "createdAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "StudentExperience_pkey" PRIMARY KEY (id),
  CONSTRAINT "StudentExperience_status_check"
    CHECK (status IN ('not_started', 'generating', 'ready', 'failed')),
  CONSTRAINT "StudentExperience_student_plan_key" UNIQUE ("studentId", "planItemId")
);

CREATE INDEX IF NOT EXISTS "StudentExperience_student_status_idx"
  ON "StudentExperience" ("studentId", status);
