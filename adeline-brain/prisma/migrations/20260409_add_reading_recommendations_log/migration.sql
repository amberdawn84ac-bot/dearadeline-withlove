-- Add ReadingRecommendationsLog table for registrar tracking
-- Tracks all book recommendations made to students for accountability and reporting

-- Create the recommendations log table
CREATE TABLE "ReadingRecommendationsLog" (
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

-- Create indexes for registrar queries
CREATE INDEX "ReadingRecommendationsLog_studentId_idx" ON "ReadingRecommendationsLog"("studentId");
CREATE INDEX "ReadingRecommendationsLog_recommendationDate_idx" ON "ReadingRecommendationsLog"("recommendationDate");
CREATE INDEX "ReadingRecommendationsLog_adaptiveLexileMin_idx" ON "ReadingRecommendationsLog"("adaptiveLexileMin");
CREATE INDEX "ReadingRecommendationsLog_adaptiveLexileMax_idx" ON "ReadingRecommendationsLog"("adaptiveLexileMax");

-- Add foreign key constraint to User table
ALTER TABLE "ReadingRecommendationsLog" ADD CONSTRAINT "ReadingRecommendationsLog_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "User"(id) ON DELETE CASCADE ON UPDATE CASCADE;
