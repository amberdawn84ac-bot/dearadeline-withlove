-- Dear Adeline: Apply all migrations
-- Run this in Supabase SQL Editor

-- ENUMS
DO $$ BEGIN
  CREATE TYPE "UserRole" AS ENUM ('STUDENT', 'PARENT', 'ADMIN');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "Track" AS ENUM ('CREATION_SCIENCE', 'HEALTH_NATUROPATHY', 'HOMESTEADING', 'GOVERNMENT_ECONOMICS', 'JUSTICE_CHANGEMAKING', 'DISCIPLESHIP', 'TRUTH_HISTORY', 'ENGLISH_LITERATURE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "BlockType" AS ENUM ('TEXT', 'PRIMARY_SOURCE', 'LAB_MISSION', 'RESEARCH_MISSION', 'QUIZ');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "EvidenceVerdict" AS ENUM ('VERIFIED', 'ARCHIVE_SILENT', 'RESEARCH_MISSION');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "DifficultyLevel" AS ENUM ('EMERGING', 'DEVELOPING', 'EXPANDING', 'MASTERING');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TYPE "BlockType" ADD VALUE IF NOT EXISTS 'NARRATIVE';

DO $$ BEGIN
  CREATE TYPE "XAPIVerb" AS ENUM ('experienced','completed','attempted','passed','failed','scored','interacted','created','shared','observed','practiced','researched','sealed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "CreditType" AS ENUM ('CORE','ELECTIVE','PHYSICAL_ED','FINE_ARTS','HOMESTEAD');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "GradeLetter" AS ENUM ('A_PLUS','A','A_MINUS','B_PLUS','B','B_MINUS','C_PLUS','C','C_MINUS','D_PLUS','D','D_MINUS','F','PASS','FAIL','INCOMPLETE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE "AgentName" AS ENUM ('HistorianAgent','ScienceAgent','DiscipleshipAgent','RegistrarAgent');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TYPE "Track" ADD VALUE IF NOT EXISTS 'APPLIED_MATHEMATICS';
ALTER TYPE "Track" ADD VALUE IF NOT EXISTS 'CREATIVE_ECONOMY';

-- EXTENSIONS
CREATE EXTENSION IF NOT EXISTS vector;

-- TABLES
CREATE TABLE IF NOT EXISTS "User" (
  "id" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "email" TEXT NOT NULL,
  "role" "UserRole" NOT NULL,
  "isHomestead" BOOLEAN NOT NULL DEFAULT false,
  "gradeLevel" TEXT,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "User_email_key" ON "User"("email");

ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "mathLevel" INTEGER;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "elaLevel" INTEGER;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "scienceLevel" INTEGER;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "historyLevel" INTEGER;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "interests" TEXT[] DEFAULT '{}';
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "learningStyle" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "pacingMultiplier" DOUBLE PRECISION;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "state" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "targetGraduationYear" INTEGER;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "onboardingComplete" BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "coppaConsent" BOOLEAN;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "parentId" TEXT;

CREATE TABLE IF NOT EXISTS "InviteCode" (
  "id" TEXT NOT NULL,
  "code" TEXT NOT NULL,
  "isUsed" BOOLEAN NOT NULL DEFAULT false,
  "claimedByEmail" TEXT,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "InviteCode_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "InviteCode_code_key" ON "InviteCode"("code");

CREATE TABLE IF NOT EXISTS "LearningRecord" (
  "id" TEXT NOT NULL,
  "studentId" TEXT NOT NULL,
  "lessonId" TEXT NOT NULL,
  "blockId" TEXT,
  "verb" "XAPIVerb" NOT NULL,
  "objectId" TEXT NOT NULL,
  "objectName" TEXT NOT NULL,
  "track" "Track" NOT NULL,
  "oasStandard" TEXT NOT NULL DEFAULT '',
  "gradeLevel" TEXT NOT NULL DEFAULT '',
  "isHomestead" BOOLEAN NOT NULL DEFAULT false,
  "agentName" "AgentName",
  "blockType" TEXT NOT NULL DEFAULT '',
  "durationMs" INTEGER,
  "completion" BOOLEAN NOT NULL DEFAULT false,
  "response" TEXT,
  "scoreRaw" DOUBLE PRECISION,
  "scoreMin" DOUBLE PRECISION,
  "scoreMax" DOUBLE PRECISION,
  "statementJson" JSONB NOT NULL DEFAULT '{}',
  "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "LearningRecord_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "LearningRecord_studentId_idx" ON "LearningRecord"("studentId");
CREATE INDEX IF NOT EXISTS "LearningRecord_lessonId_idx" ON "LearningRecord"("lessonId");
CREATE INDEX IF NOT EXISTS "LearningRecord_track_idx" ON "LearningRecord"("track");

CREATE TABLE IF NOT EXISTS "TranscriptEntry" (
  "id" TEXT NOT NULL,
  "studentId" TEXT NOT NULL,
  "lessonId" TEXT NOT NULL,
  "courseTitle" TEXT NOT NULL,
  "track" "Track" NOT NULL,
  "oasStandards" TEXT[] NOT NULL DEFAULT '{}',
  "activityDescription" TEXT NOT NULL DEFAULT '',
  "creditHours" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  "creditType" "CreditType" NOT NULL DEFAULT 'ELECTIVE',
  "gradeLetter" "GradeLetter",
  "percentScore" DOUBLE PRECISION,
  "isHomesteadCredit" BOOLEAN NOT NULL DEFAULT false,
  "agentName" "AgentName",
  "researcherActivated" BOOLEAN NOT NULL DEFAULT false,
  "completedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "sealedAt" TIMESTAMP(3),
  "xapiStatementId" TEXT,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "TranscriptEntry_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "TranscriptEntry_studentId_lessonId_key" ON "TranscriptEntry"("studentId","lessonId");
CREATE INDEX IF NOT EXISTS "TranscriptEntry_studentId_idx" ON "TranscriptEntry"("studentId");
CREATE INDEX IF NOT EXISTS "TranscriptEntry_completedAt_idx" ON "TranscriptEntry"("completedAt");

CREATE TABLE IF NOT EXISTS "SpacedRepetitionCard" (
  "id" TEXT NOT NULL,
  "studentId" TEXT NOT NULL,
  "conceptId" TEXT NOT NULL,
  "conceptName" TEXT NOT NULL,
  "track" "Track" NOT NULL,
  "interval" INTEGER NOT NULL DEFAULT 1,
  "easeFactor" DOUBLE PRECISION NOT NULL DEFAULT 2.5,
  "repetitions" INTEGER NOT NULL DEFAULT 0,
  "lastQuality" INTEGER,
  "masteryLevel" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  "dueAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "lastReviewedAt" TIMESTAMP(3),
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "SpacedRepetitionCard_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "SpacedRepetitionCard_studentId_conceptId_key" ON "SpacedRepetitionCard"("studentId","conceptId");
CREATE INDEX IF NOT EXISTS "SpacedRepetitionCard_studentId_idx" ON "SpacedRepetitionCard"("studentId");
CREATE INDEX IF NOT EXISTS "SpacedRepetitionCard_dueAt_idx" ON "SpacedRepetitionCard"("dueAt");

CREATE TABLE IF NOT EXISTS "HippocampusDocument" (
  "id" TEXT NOT NULL,
  "source_title" TEXT NOT NULL,
  "source_url" TEXT NOT NULL,
  "source_type" TEXT NOT NULL DEFAULT 'PRIMARY_SOURCE',
  "chunk" TEXT NOT NULL,
  "embedding" vector(1536) NOT NULL,
  "citation_author" TEXT NOT NULL DEFAULT '',
  "citation_year" INTEGER,
  "citation_archive_name" TEXT NOT NULL DEFAULT '',
  "track" TEXT NOT NULL,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "HippocampusDocument_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "HippocampusDocument_source_url_track_key" ON "HippocampusDocument"("source_url","track");
CREATE INDEX IF NOT EXISTS "HippocampusDocument_track_idx" ON "HippocampusDocument"("track");

CREATE TABLE IF NOT EXISTS "Book" (
  "id" TEXT NOT NULL,
  "title" TEXT NOT NULL,
  "author" TEXT NOT NULL,
  "coverUrl" TEXT,
  "sourceLibrary" TEXT NOT NULL,
  "source_url" TEXT,
  "lexile_level" INTEGER,
  "grade_band" TEXT,
  "description" TEXT,
  "track" TEXT NOT NULL,
  "embedding" vector(1536),
  CONSTRAINT "Book_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "Book_source_url_unique" ON "Book"("source_url");
CREATE INDEX IF NOT EXISTS "Book_track_idx" ON "Book"("track");
CREATE INDEX IF NOT EXISTS "Book_embedding_idx" ON "Book" USING hnsw ("embedding" vector_cosine_ops);

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
  CONSTRAINT "ReadingSession_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "ReadingSession_studentId_bookId_key" ON "ReadingSession"("studentId","bookId");
CREATE INDEX IF NOT EXISTS "ReadingSession_studentId_idx" ON "ReadingSession"("studentId");

CREATE TABLE IF NOT EXISTS "ReadingRecommendationsLog" (
  id TEXT NOT NULL,
  "studentId" TEXT NOT NULL,
  "recommendedBookIds" TEXT[] NOT NULL,
  "adaptiveLexileMin" INTEGER NOT NULL,
  "adaptiveLexileMax" INTEGER NOT NULL,
  "confidenceScore" REAL NOT NULL,
  "recommendationDate" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "gradeLevel" TEXT,
  "interests" TEXT[],
  CONSTRAINT "ReadingRecommendationsLog_pkey" PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS "ReadingRecommendationsLog_studentId_idx" ON "ReadingRecommendationsLog"("studentId");
