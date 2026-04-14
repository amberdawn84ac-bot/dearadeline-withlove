-- apply_all.sql — Run this once to bring the database fully up to date.
-- Safe to run against a DB that already has InviteCode + student_journal.
-- All CREATE statements use IF NOT EXISTS. All ALTER TYPE uses IF NOT EXISTS.

-- ── Enums ─────────────────────────────────────────────────────────────────────

DO $$ BEGIN
  CREATE TYPE "UserRole" AS ENUM ('STUDENT', 'PARENT', 'ADMIN');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "Track" AS ENUM (
    'CREATION_SCIENCE', 'HEALTH_NATUROPATHY', 'HOMESTEADING',
    'GOVERNMENT_ECONOMICS', 'JUSTICE_CHANGEMAKING', 'DISCIPLESHIP',
    'TRUTH_HISTORY', 'ENGLISH_LITERATURE'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TYPE "Track" ADD VALUE IF NOT EXISTS 'APPLIED_MATHEMATICS';
ALTER TYPE "Track" ADD VALUE IF NOT EXISTS 'CREATIVE_ECONOMY';

DO $$ BEGIN
  CREATE TYPE "BlockType" AS ENUM ('TEXT', 'PRIMARY_SOURCE', 'LAB_MISSION', 'RESEARCH_MISSION', 'QUIZ');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TYPE "BlockType" ADD VALUE IF NOT EXISTS 'NARRATIVE';

DO $$ BEGIN
  CREATE TYPE "EvidenceVerdict" AS ENUM ('VERIFIED', 'ARCHIVE_SILENT', 'RESEARCH_MISSION');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "DifficultyLevel" AS ENUM ('EMERGING', 'DEVELOPING', 'EXPANDING', 'MASTERING');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "XAPIVerb" AS ENUM (
    'experienced', 'completed', 'attempted', 'passed', 'failed',
    'scored', 'interacted', 'created', 'shared', 'observed',
    'practiced', 'researched', 'sealed'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "CreditType" AS ENUM ('CORE', 'ELECTIVE', 'PHYSICAL_ED', 'FINE_ARTS', 'HOMESTEAD');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "GradeLetter" AS ENUM (
    'A_PLUS', 'A', 'A_MINUS', 'B_PLUS', 'B', 'B_MINUS',
    'C_PLUS', 'C', 'C_MINUS', 'D_PLUS', 'D', 'D_MINUS',
    'F', 'PASS', 'FAIL', 'INCOMPLETE'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "AgentName" AS ENUM (
    'HistorianAgent', 'ScienceAgent', 'DiscipleshipAgent', 'RegistrarAgent'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Tables ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS "User" (
    "id"          TEXT      NOT NULL,
    "name"        TEXT      NOT NULL,
    "email"       TEXT      NOT NULL,
    "role"        "UserRole" NOT NULL,
    "isHomestead" BOOLEAN   NOT NULL DEFAULT false,
    "gradeLevel"  TEXT,
    "createdAt"   TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"   TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "User_email_key" ON "User"("email");
CREATE INDEX IF NOT EXISTS "User_role_idx"  ON "User"("role");
CREATE INDEX IF NOT EXISTS "User_email_idx" ON "User"("email");

CREATE TABLE IF NOT EXISTS "Lesson" (
    "id"               TEXT NOT NULL,
    "title"            TEXT NOT NULL,
    "estimatedMinutes" INTEGER NOT NULL,
    "targetGrades"     TEXT[],
    "createdAt"        TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"        TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Lesson_pkey" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "LessonTrack" (
    "lessonId" TEXT    NOT NULL,
    "track"    "Track" NOT NULL,
    CONSTRAINT "LessonTrack_pkey" PRIMARY KEY ("lessonId", "track")
);

CREATE TABLE IF NOT EXISTS "LessonBlock" (
    "id"                 TEXT             NOT NULL,
    "lessonId"           TEXT             NOT NULL,
    "track"              "Track"          NOT NULL,
    "blockType"          "BlockType"      NOT NULL,
    "difficulty"         "DifficultyLevel" NOT NULL,
    "order"              INTEGER          NOT NULL,
    "title"              TEXT             NOT NULL,
    "content"            TEXT             NOT NULL,
    "isSilenced"         BOOLEAN          NOT NULL DEFAULT false,
    "tags"               TEXT[],
    "homesteadEnabled"   BOOLEAN          NOT NULL DEFAULT false,
    "homesteadContent"   TEXT,
    "homesteadPractical" TEXT,
    "createdAt"          TIMESTAMP(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "LessonBlock_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "LessonBlock_lessonId_order_idx" ON "LessonBlock"("lessonId", "order");
CREATE INDEX IF NOT EXISTS "LessonBlock_blockType_idx"      ON "LessonBlock"("blockType");

CREATE TABLE IF NOT EXISTS "Evidence" (
    "id"                  TEXT             NOT NULL,
    "blockId"             TEXT             NOT NULL,
    "sourceTitle"         TEXT             NOT NULL,
    "sourceUrl"           TEXT             NOT NULL,
    "similarityScore"     DOUBLE PRECISION NOT NULL,
    "verdict"             "EvidenceVerdict" NOT NULL,
    "chunk"               TEXT             NOT NULL,
    "retrievedAt"         TIMESTAMP(3)     NOT NULL,
    "citationAuthor"      TEXT             NOT NULL DEFAULT '',
    "citationYear"        INTEGER          NOT NULL DEFAULT 0,
    "citationArchiveName" TEXT             NOT NULL DEFAULT '',
    CONSTRAINT "Evidence_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "Evidence_blockId_idx"         ON "Evidence"("blockId");
CREATE INDEX IF NOT EXISTS "Evidence_verdict_idx"         ON "Evidence"("verdict");
CREATE INDEX IF NOT EXISTS "Evidence_similarityScore_idx" ON "Evidence"("similarityScore");

CREATE TABLE IF NOT EXISTS "StudentLesson" (
    "studentId"   TEXT NOT NULL,
    "lessonId"    TEXT NOT NULL,
    "startedAt"   TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAt" TIMESTAMP(3),
    CONSTRAINT "StudentLesson_pkey" PRIMARY KEY ("studentId", "lessonId")
);

CREATE TABLE IF NOT EXISTS "InviteCode" (
    "id"             TEXT    NOT NULL,
    "code"           TEXT    NOT NULL,
    "isUsed"         BOOLEAN NOT NULL DEFAULT false,
    "claimedByEmail" TEXT,
    "createdAt"      TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "InviteCode_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "InviteCode_code_key" ON "InviteCode"("code");
CREATE INDEX IF NOT EXISTS "InviteCode_code_idx"        ON "InviteCode"("code");

CREATE TABLE IF NOT EXISTS "LearningRecord" (
    "id"            TEXT             NOT NULL,
    "studentId"     TEXT             NOT NULL,
    "lessonId"      TEXT             NOT NULL,
    "blockId"       TEXT,
    "verb"          "XAPIVerb"       NOT NULL,
    "objectId"      TEXT             NOT NULL,
    "objectName"    TEXT             NOT NULL,
    "track"         "Track"          NOT NULL,
    "oasStandard"   TEXT             NOT NULL DEFAULT '',
    "gradeLevel"    TEXT             NOT NULL DEFAULT '',
    "isHomestead"   BOOLEAN          NOT NULL DEFAULT false,
    "agentName"     "AgentName",
    "blockType"     TEXT             NOT NULL DEFAULT '',
    "durationMs"    INTEGER,
    "completion"    BOOLEAN          NOT NULL DEFAULT false,
    "response"      TEXT,
    "scoreRaw"      DOUBLE PRECISION,
    "scoreMin"      DOUBLE PRECISION,
    "scoreMax"      DOUBLE PRECISION,
    "statementJson" JSONB            NOT NULL DEFAULT '{}',
    "timestamp"     TIMESTAMP(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdAt"     TIMESTAMP(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "LearningRecord_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "LearningRecord_studentId_idx" ON "LearningRecord"("studentId");
CREATE INDEX IF NOT EXISTS "LearningRecord_lessonId_idx"  ON "LearningRecord"("lessonId");
CREATE INDEX IF NOT EXISTS "LearningRecord_track_idx"     ON "LearningRecord"("track");
CREATE INDEX IF NOT EXISTS "LearningRecord_verb_idx"      ON "LearningRecord"("verb");
CREATE INDEX IF NOT EXISTS "LearningRecord_timestamp_idx" ON "LearningRecord"("timestamp");

CREATE TABLE IF NOT EXISTS "TranscriptEntry" (
    "id"                  TEXT             NOT NULL,
    "studentId"           TEXT             NOT NULL,
    "lessonId"            TEXT             NOT NULL,
    "courseTitle"         TEXT             NOT NULL,
    "track"               "Track"          NOT NULL,
    "oasStandards"        TEXT[]           NOT NULL DEFAULT '{}',
    "activityDescription" TEXT             NOT NULL DEFAULT '',
    "creditHours"         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "creditType"          "CreditType"     NOT NULL DEFAULT 'ELECTIVE',
    "gradeLetter"         "GradeLetter",
    "percentScore"        DOUBLE PRECISION,
    "isHomesteadCredit"   BOOLEAN          NOT NULL DEFAULT false,
    "agentName"           "AgentName",
    "researcherActivated" BOOLEAN          NOT NULL DEFAULT false,
    "completedAt"         TIMESTAMP(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "sealedAt"            TIMESTAMP(3),
    "xapiStatementId"     TEXT,
    "createdAt"           TIMESTAMP(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "TranscriptEntry_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "TranscriptEntry_studentId_lessonId_key"
    ON "TranscriptEntry"("studentId", "lessonId");
CREATE INDEX IF NOT EXISTS "TranscriptEntry_studentId_idx"   ON "TranscriptEntry"("studentId");
CREATE INDEX IF NOT EXISTS "TranscriptEntry_track_idx"       ON "TranscriptEntry"("track");
CREATE INDEX IF NOT EXISTS "TranscriptEntry_creditType_idx"  ON "TranscriptEntry"("creditType");
CREATE INDEX IF NOT EXISTS "TranscriptEntry_completedAt_idx" ON "TranscriptEntry"("completedAt");

CREATE TABLE IF NOT EXISTS "SpacedRepetitionCard" (
    "id"             TEXT             NOT NULL,
    "studentId"      TEXT             NOT NULL,
    "conceptId"      TEXT             NOT NULL,
    "conceptName"    TEXT             NOT NULL,
    "track"          "Track"          NOT NULL,
    "interval"       INTEGER          NOT NULL DEFAULT 1,
    "easeFactor"     DOUBLE PRECISION NOT NULL DEFAULT 2.5,
    "repetitions"    INTEGER          NOT NULL DEFAULT 0,
    "lastQuality"    INTEGER,
    "masteryLevel"   DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "dueAt"          TIMESTAMP(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "lastReviewedAt" TIMESTAMP(3),
    "createdAt"      TIMESTAMP(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"      TIMESTAMP(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "SpacedRepetitionCard_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "SpacedRepetitionCard_studentId_conceptId_key"
    ON "SpacedRepetitionCard"("studentId", "conceptId");
CREATE INDEX IF NOT EXISTS "SpacedRepetitionCard_studentId_idx"    ON "SpacedRepetitionCard"("studentId");
CREATE INDEX IF NOT EXISTS "SpacedRepetitionCard_dueAt_idx"        ON "SpacedRepetitionCard"("dueAt");
CREATE INDEX IF NOT EXISTS "SpacedRepetitionCard_track_idx"        ON "SpacedRepetitionCard"("track");
CREATE INDEX IF NOT EXISTS "SpacedRepetitionCard_masteryLevel_idx" ON "SpacedRepetitionCard"("masteryLevel");

-- ── 2026-04-02: HippocampusDocument (pgvector embeddings) ──────────────────────

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS "HippocampusDocument" (
    "id"                      TEXT          NOT NULL,
    "source_title"            TEXT          NOT NULL,
    "source_url"              TEXT          NOT NULL,
    "source_type"             TEXT          NOT NULL DEFAULT 'PRIMARY_SOURCE',
    "chunk"                   TEXT          NOT NULL,
    "embedding"               vector(1536)  NOT NULL,
    "citation_author"         TEXT          NOT NULL DEFAULT '',
    "citation_year"           INTEGER,
    "citation_archive_name"   TEXT          NOT NULL DEFAULT '',
    "track"                   TEXT          NOT NULL,
    "created_at"              TIMESTAMP(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at"              TIMESTAMP(3)  NOT NULL,
    CONSTRAINT "HippocampusDocument_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "HippocampusDocument_source_url_track_key"
    ON "HippocampusDocument"("source_url", "track");
CREATE INDEX IF NOT EXISTS "HippocampusDocument_track_idx" ON "HippocampusDocument"("track");
CREATE INDEX IF NOT EXISTS "HippocampusDocument_source_url_idx" ON "HippocampusDocument"("source_url");
CREATE INDEX IF NOT EXISTS "HippocampusDocument_embedding_idx"
    ON "HippocampusDocument" USING ivfflat ("embedding" vector_cosine_ops) WITH (lists = 100);

-- ── 2026-04-03: User onboarding fields ───────────────────────────────────────

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "mathLevel" INTEGER;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "elaLevel" INTEGER;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "scienceLevel" INTEGER;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "historyLevel" INTEGER;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "interests" TEXT[] DEFAULT '{}';
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "learningStyle" TEXT;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "pacingMultiplier" DOUBLE PRECISION;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "state" TEXT;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "targetGraduationYear" INTEGER;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "User" ADD COLUMN "onboardingComplete" BOOLEAN NOT NULL DEFAULT false;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS "User_onboardingComplete_idx" ON "User"("onboardingComplete");

-- ── 2026-04-04: Book table extensions for Bookshelf v1 ─────────────────────────

DO $$ BEGIN
  ALTER TABLE "Book" ADD COLUMN "source_url" TEXT;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "Book" ADD COLUMN "lexile_level" INTEGER;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "Book" ADD COLUMN "grade_band" TEXT;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "Book" ADD COLUMN "description" TEXT;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "Book" ADD COLUMN "track" TEXT NOT NULL DEFAULT '';
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "Book" ADD COLUMN "embedding" vector(1536);
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE "Book" ADD CONSTRAINT "Book_source_url_unique" UNIQUE ("source_url");
EXCEPTION WHEN duplicate_table OR unique_violation THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS "Book_track_idx" ON "Book"("track");
CREATE INDEX IF NOT EXISTS "Book_lexile_level_idx" ON "Book"("lexile_level");
CREATE INDEX IF NOT EXISTS "Book_sourceLibrary_idx" ON "Book"("sourceLibrary");
CREATE INDEX IF NOT EXISTS "Book_embedding_idx" ON "Book" USING hnsw ("embedding" vector_cosine_ops);

-- ── 2026-04-04: ReadingSession table ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS "ReadingSession" (
    "id" TEXT NOT NULL,
    "studentId" TEXT NOT NULL,
    "bookId" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAt" TIMESTAMP(3),
    "pagesRead" INTEGER NOT NULL DEFAULT 0,
    "totalPages" INTEGER,
    "currentLocation" TEXT,
    "studentReflection" TEXT,
    "readingMinutes" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "ReadingSession_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "ReadingSession_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "User" ("id") ON DELETE CASCADE,
    CONSTRAINT "ReadingSession_bookId_fkey" FOREIGN KEY ("bookId") REFERENCES "Book" ("id") ON DELETE CASCADE,
    CONSTRAINT "ReadingSession_status_check" CHECK ("status" IN ('reading', 'finished', 'wishlist'))
);

CREATE UNIQUE INDEX IF NOT EXISTS "ReadingSession_studentId_bookId_key" ON "ReadingSession"("studentId", "bookId");
CREATE INDEX IF NOT EXISTS "ReadingSession_studentId_idx" ON "ReadingSession"("studentId");
CREATE INDEX IF NOT EXISTS "ReadingSession_bookId_idx" ON "ReadingSession"("bookId");
CREATE INDEX IF NOT EXISTS "ReadingSession_status_idx" ON "ReadingSession"("status");

-- ── 2026-04-09: ReadingRecommendationsLog table ───────────────────────────────

CREATE TABLE IF NOT EXISTS "ReadingRecommendationsLog" (
    "id" TEXT NOT NULL,
    "studentId" TEXT NOT NULL,
    "recommendedBookIds" TEXT[] NOT NULL,
    "adaptiveLexileMin" INTEGER NOT NULL,
    "adaptiveLexileMax" INTEGER NOT NULL,
    "confidenceScore" REAL NOT NULL,
    "recommendationDate" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "gradeLevel" TEXT,
    "interests" TEXT[],
    CONSTRAINT "ReadingRecommendationsLog_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "ReadingRecommendationsLog_studentId_idx" ON "ReadingRecommendationsLog"("studentId");
CREATE INDEX IF NOT EXISTS "ReadingRecommendationsLog_recommendationDate_idx" ON "ReadingRecommendationsLog"("recommendationDate");
CREATE INDEX IF NOT EXISTS "ReadingRecommendationsLog_adaptiveLexileMin_idx" ON "ReadingRecommendationsLog"("adaptiveLexileMin");
CREATE INDEX IF NOT EXISTS "ReadingRecommendationsLog_adaptiveLexileMax_idx" ON "ReadingRecommendationsLog"("adaptiveLexileMax");

DO $$ BEGIN
  ALTER TABLE "ReadingRecommendationsLog" ADD CONSTRAINT "ReadingRecommendationsLog_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── 2026-04-12: CanonicalLesson table ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS "CanonicalLesson" (
    "id" TEXT NOT NULL,
    "topicSlug" TEXT NOT NULL,
    "topic" TEXT NOT NULL,
    "track" "Track" NOT NULL,
    "title" TEXT NOT NULL,
    "blocksJson" JSONB NOT NULL,
    "oasStandards" JSONB NOT NULL DEFAULT '[]',
    "researcherActivated" BOOLEAN NOT NULL DEFAULT false,
    "agentName" TEXT NOT NULL DEFAULT '',
    "generatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "CanonicalLesson_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "CanonicalLesson_topicSlug_key" ON "CanonicalLesson"("topicSlug");
CREATE INDEX IF NOT EXISTS "CanonicalLesson_track_idx" ON "CanonicalLesson"("track");

-- 2026-04-14: Add human-in-the-loop review columns
ALTER TABLE "CanonicalLesson"
  ADD COLUMN IF NOT EXISTS "pendingApproval"   BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS "needsReviewReason" TEXT;

CREATE INDEX IF NOT EXISTS "CanonicalLesson_pending_idx"
  ON "CanonicalLesson" ("pendingApproval")
  WHERE "pendingApproval" = TRUE;
