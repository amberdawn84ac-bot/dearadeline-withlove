CREATE TABLE "StudentCreditProfile" (
 "studentId" TEXT PRIMARY KEY REFERENCES "User"(id),
 "profileKey" TEXT NOT NULL,
 "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE "CourseScope" (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
 "studentId" TEXT NOT NULL REFERENCES "User"(id),
 title TEXT NOT NULL, track "Track" NOT NULL, bucket TEXT NOT NULL,
 "creditUnits" DOUBLE PRECISION NOT NULL CHECK ("creditUnits" > 0 AND "creditUnits" <= 2),
 "skillIds" TEXT[] NOT NULL CHECK (cardinality("skillIds") > 0),
 rationale TEXT NOT NULL,
 "createdBy" TEXT NOT NULL,
 "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX "CourseScope_student" ON "CourseScope"("studentId");
CREATE TABLE "CourseAward" (
 "scopeId" TEXT PRIMARY KEY REFERENCES "CourseScope"(id),
 "studentId" TEXT NOT NULL REFERENCES "User"(id),
 "approvedBy" TEXT NOT NULL, snapshot JSONB NOT NULL,
 "transcriptId" TEXT NOT NULL UNIQUE REFERENCES "TranscriptEntry"(id),
 "approvedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- One demonstrated skill cannot silently earn credit in several courses.
CREATE TABLE "CourseSkillAllocation" (
 "studentId" TEXT NOT NULL REFERENCES "User"(id),
 "skillId" TEXT NOT NULL,
 "scopeId" TEXT NOT NULL REFERENCES "CourseAward"("scopeId"),
 PRIMARY KEY ("studentId", "skillId")
);
CREATE TABLE "ClassroomAssessment" (
 "attemptId" TEXT PRIMARY KEY REFERENCES "EvidenceAttempt"(id),
 "studentId" TEXT NOT NULL REFERENCES "User"(id),
 status TEXT NOT NULL CHECK (status IN ('reviewed','needs_review','unmapped')),
 review JSONB NOT NULL,
 "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);
