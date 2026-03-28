-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('STUDENT', 'PARENT', 'ADMIN');

-- CreateEnum
CREATE TYPE "Track" AS ENUM ('CREATION_SCIENCE', 'HEALTH_NATUROPATHY', 'HOMESTEADING', 'GOVERNMENT_ECONOMICS', 'JUSTICE_CHANGEMAKING', 'DISCIPLESHIP', 'TRUTH_HISTORY', 'ENGLISH_LITERATURE');

-- CreateEnum
CREATE TYPE "BlockType" AS ENUM ('TEXT', 'PRIMARY_SOURCE', 'LAB_MISSION', 'RESEARCH_MISSION', 'QUIZ');

-- CreateEnum
CREATE TYPE "EvidenceVerdict" AS ENUM ('VERIFIED', 'ARCHIVE_SILENT', 'RESEARCH_MISSION');

-- CreateEnum
CREATE TYPE "DifficultyLevel" AS ENUM ('EMERGING', 'DEVELOPING', 'EXPANDING', 'MASTERING');

-- CreateTable
CREATE TABLE "User" (
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

-- CreateTable
CREATE TABLE "Lesson" (
    "id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "estimatedMinutes" INTEGER NOT NULL,
    "targetGrades" TEXT[],
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Lesson_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "LessonTrack" (
    "lessonId" TEXT NOT NULL,
    "track" "Track" NOT NULL,

    CONSTRAINT "LessonTrack_pkey" PRIMARY KEY ("lessonId","track")
);

-- CreateTable
CREATE TABLE "LessonBlock" (
    "id" TEXT NOT NULL,
    "lessonId" TEXT NOT NULL,
    "track" "Track" NOT NULL,
    "blockType" "BlockType" NOT NULL,
    "difficulty" "DifficultyLevel" NOT NULL,
    "order" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "isSilenced" BOOLEAN NOT NULL DEFAULT false,
    "tags" TEXT[],
    "homesteadEnabled" BOOLEAN NOT NULL DEFAULT false,
    "homesteadContent" TEXT,
    "homesteadPractical" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "LessonBlock_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Evidence" (
    "id" TEXT NOT NULL,
    "blockId" TEXT NOT NULL,
    "sourceTitle" TEXT NOT NULL,
    "sourceUrl" TEXT NOT NULL,
    "similarityScore" DOUBLE PRECISION NOT NULL,
    "verdict" "EvidenceVerdict" NOT NULL,
    "chunk" TEXT NOT NULL,
    "retrievedAt" TIMESTAMP(3) NOT NULL,
    "citationAuthor" TEXT NOT NULL,
    "citationYear" INTEGER NOT NULL,
    "citationArchiveName" TEXT NOT NULL,

    CONSTRAINT "Evidence_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "StudentLesson" (
    "studentId" TEXT NOT NULL,
    "lessonId" TEXT NOT NULL,
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAt" TIMESTAMP(3),

    CONSTRAINT "StudentLesson_pkey" PRIMARY KEY ("studentId","lessonId")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE INDEX "User_role_idx" ON "User"("role");

-- CreateIndex
CREATE INDEX "User_email_idx" ON "User"("email");

-- CreateIndex
CREATE INDEX "LessonBlock_lessonId_order_idx" ON "LessonBlock"("lessonId", "order");

-- CreateIndex
CREATE INDEX "LessonBlock_blockType_idx" ON "LessonBlock"("blockType");

-- CreateIndex
CREATE INDEX "Evidence_blockId_idx" ON "Evidence"("blockId");

-- CreateIndex
CREATE INDEX "Evidence_verdict_idx" ON "Evidence"("verdict");

-- CreateIndex
CREATE INDEX "Evidence_similarityScore_idx" ON "Evidence"("similarityScore");

-- AddForeignKey
ALTER TABLE "LessonTrack" ADD CONSTRAINT "LessonTrack_lessonId_fkey" FOREIGN KEY ("lessonId") REFERENCES "Lesson"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LessonBlock" ADD CONSTRAINT "LessonBlock_lessonId_fkey" FOREIGN KEY ("lessonId") REFERENCES "Lesson"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_blockId_fkey" FOREIGN KEY ("blockId") REFERENCES "LessonBlock"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "StudentLesson" ADD CONSTRAINT "StudentLesson_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "StudentLesson" ADD CONSTRAINT "StudentLesson_lessonId_fkey" FOREIGN KEY ("lessonId") REFERENCES "Lesson"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
