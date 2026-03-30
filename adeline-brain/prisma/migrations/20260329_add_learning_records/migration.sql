-- Phase 6: xAPI Learning Records, CASE Transcript Entries, Spaced Repetition Cards
-- Adds persistence layer for the RegistrarAgent outputs (Phase 3)
-- and the SM-2 spaced repetition engine (Phase 2).

-- ── New enum values ────────────────────────────────────────────────────────────

-- NARRATIVE block type (used by DiscipleshipAgent)
ALTER TYPE "BlockType" ADD VALUE IF NOT EXISTS 'NARRATIVE';

-- xAPI verb set (mirrors xAPIVerb in adeline-core/src/schemas/learningActivity.ts)
CREATE TYPE "XAPIVerb" AS ENUM (
    'experienced',
    'completed',
    'attempted',
    'passed',
    'failed',
    'scored',
    'interacted',
    'created',
    'shared',
    'observed',
    'practiced',
    'researched',
    'sealed'
);

-- CASE credit types (mirrors CreditType in adeline-core/src/schemas/transcript.ts)
CREATE TYPE "CreditType" AS ENUM (
    'CORE',
    'ELECTIVE',
    'PHYSICAL_ED',
    'FINE_ARTS',
    'HOMESTEAD'
);

-- Grade letter values
CREATE TYPE "GradeLetter" AS ENUM (
    'A_PLUS', 'A', 'A_MINUS',
    'B_PLUS', 'B', 'B_MINUS',
    'C_PLUS', 'C', 'C_MINUS',
    'D_PLUS', 'D', 'D_MINUS',
    'F', 'PASS', 'FAIL', 'INCOMPLETE'
);

-- Agent name enum (mirrors AgentName in adeline-core)
CREATE TYPE "AgentName" AS ENUM (
    'HistorianAgent',
    'ScienceAgent',
    'DiscipleshipAgent',
    'RegistrarAgent'
);

-- ── LearningRecord (xAPI statement per block) ──────────────────────────────────
-- One row per block per lesson session.
-- actor = student, verb = xAPI verb, object = lesson block.
-- Raw xAPI JSON stored in statement_json for full fidelity.

CREATE TABLE "LearningRecord" (
    "id"             TEXT        NOT NULL,
    "studentId"      TEXT        NOT NULL,
    "lessonId"       TEXT        NOT NULL,
    "blockId"        TEXT,                       -- NULL for lesson-level statements
    "verb"           "XAPIVerb"  NOT NULL,
    "objectId"       TEXT        NOT NULL,       -- IRI e.g. urn:adeline:lesson:uuid:block:0
    "objectName"     TEXT        NOT NULL,
    "track"          "Track"     NOT NULL,
    "oasStandard"    TEXT        NOT NULL DEFAULT '',
    "gradeLevel"     TEXT        NOT NULL DEFAULT '',
    "isHomestead"    BOOLEAN     NOT NULL DEFAULT false,
    "agentName"      "AgentName",
    "blockType"      TEXT        NOT NULL DEFAULT '',
    "durationMs"     INTEGER,
    "completion"     BOOLEAN     NOT NULL DEFAULT false,
    "response"       TEXT,
    "scoreRaw"       DOUBLE PRECISION,
    "scoreMin"       DOUBLE PRECISION,
    "scoreMax"       DOUBLE PRECISION,
    "statementJson"  JSONB       NOT NULL DEFAULT '{}',
    "timestamp"      TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdAt"      TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "LearningRecord_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "LearningRecord_studentId_idx"  ON "LearningRecord"("studentId");
CREATE INDEX "LearningRecord_lessonId_idx"   ON "LearningRecord"("lessonId");
CREATE INDEX "LearningRecord_track_idx"      ON "LearningRecord"("track");
CREATE INDEX "LearningRecord_verb_idx"       ON "LearningRecord"("verb");
CREATE INDEX "LearningRecord_timestamp_idx"  ON "LearningRecord"("timestamp");

-- ── TranscriptEntry (CASE credit per lesson) ───────────────────────────────────
-- One row per sealed lesson.
-- Represents a CASE-compatible academic credit entry for the student's transcript.

CREATE TABLE "TranscriptEntry" (
    "id"                  TEXT            NOT NULL,
    "studentId"           TEXT            NOT NULL,
    "lessonId"            TEXT            NOT NULL,
    "courseTitle"         TEXT            NOT NULL,
    "track"               "Track"         NOT NULL,
    "oasStandards"        TEXT[]          NOT NULL DEFAULT '{}',
    "activityDescription" TEXT            NOT NULL DEFAULT '',
    "creditHours"         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "creditType"          "CreditType"    NOT NULL DEFAULT 'ELECTIVE',
    "gradeLetter"         "GradeLetter",
    "percentScore"        DOUBLE PRECISION,
    "isHomesteadCredit"   BOOLEAN         NOT NULL DEFAULT false,
    "agentName"           "AgentName",
    "researcherActivated" BOOLEAN         NOT NULL DEFAULT false,
    "completedAt"         TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "sealedAt"            TIMESTAMP(3),
    "xapiStatementId"     TEXT,           -- Link to root xAPI statement for this lesson
    "createdAt"           TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "TranscriptEntry_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "TranscriptEntry_studentId_idx"    ON "TranscriptEntry"("studentId");
CREATE INDEX "TranscriptEntry_track_idx"        ON "TranscriptEntry"("track");
CREATE INDEX "TranscriptEntry_creditType_idx"   ON "TranscriptEntry"("creditType");
CREATE INDEX "TranscriptEntry_completedAt_idx"  ON "TranscriptEntry"("completedAt");
-- Unique per student+lesson (one CASE credit entry per sealed lesson)
CREATE UNIQUE INDEX "TranscriptEntry_studentId_lessonId_key"
    ON "TranscriptEntry"("studentId", "lessonId");

-- ── SpacedRepetitionCard (SM-2 state per student per concept) ─────────────────
-- Stores the SM-2 interval, ease factor, and mastery level per card.
-- Updated by the /lesson/reviews endpoint after each recall rating.

CREATE TABLE "SpacedRepetitionCard" (
    "id"             TEXT            NOT NULL,
    "studentId"      TEXT            NOT NULL,
    "conceptId"      TEXT            NOT NULL,   -- Concept node ID in Neo4j
    "conceptName"    TEXT            NOT NULL,
    "track"          "Track"         NOT NULL,
    "interval"       INTEGER         NOT NULL DEFAULT 1,      -- Days until next review
    "easeFactor"     DOUBLE PRECISION NOT NULL DEFAULT 2.5,   -- SM-2 ease factor (min 1.3)
    "repetitions"    INTEGER         NOT NULL DEFAULT 0,      -- Successful recall streak
    "lastQuality"    INTEGER,                                  -- 0–5 quality from last review
    "masteryLevel"   DOUBLE PRECISION NOT NULL DEFAULT 0.0,   -- 0.0–1.0 BKT-blended
    "dueAt"          TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "lastReviewedAt" TIMESTAMP(3),
    "createdAt"      TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"      TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "SpacedRepetitionCard_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "SpacedRepetitionCard_studentId_conceptId_key"
    ON "SpacedRepetitionCard"("studentId", "conceptId");
CREATE INDEX "SpacedRepetitionCard_studentId_idx"  ON "SpacedRepetitionCard"("studentId");
CREATE INDEX "SpacedRepetitionCard_dueAt_idx"      ON "SpacedRepetitionCard"("dueAt");
CREATE INDEX "SpacedRepetitionCard_track_idx"      ON "SpacedRepetitionCard"("track");
CREATE INDEX "SpacedRepetitionCard_masteryLevel_idx" ON "SpacedRepetitionCard"("masteryLevel");

-- ── Foreign keys (non-blocking — student may not exist in User table in dev) ───
-- FK to User is advisory; lesson records can be created before full auth.
-- Uncomment in production once User FK enforcement is confirmed:
--
-- ALTER TABLE "LearningRecord"
--   ADD CONSTRAINT "LearningRecord_studentId_fkey"
--   FOREIGN KEY ("studentId") REFERENCES "User"("id") ON DELETE SET NULL;
--
-- ALTER TABLE "TranscriptEntry"
--   ADD CONSTRAINT "TranscriptEntry_studentId_fkey"
--   FOREIGN KEY ("studentId") REFERENCES "User"("id") ON DELETE SET NULL;
--
-- ALTER TABLE "SpacedRepetitionCard"
--   ADD CONSTRAINT "SpacedRepetitionCard_studentId_fkey"
--   FOREIGN KEY ("studentId") REFERENCES "User"("id") ON DELETE CASCADE;
