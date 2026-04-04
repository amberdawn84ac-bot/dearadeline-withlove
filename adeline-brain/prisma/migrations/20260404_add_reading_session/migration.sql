-- Create reading_session table for bookshelf feature

CREATE TABLE "ReadingSession" (
  "id" TEXT NOT NULL PRIMARY KEY,
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
  CONSTRAINT "ReadingSession_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "User" ("id") ON DELETE CASCADE,
  CONSTRAINT "ReadingSession_bookId_fkey" FOREIGN KEY ("bookId") REFERENCES "Book" ("id") ON DELETE CASCADE,
  CONSTRAINT "ReadingSession_status_check" CHECK ("status" IN ('reading', 'finished', 'wishlist'))
);

-- Create UNIQUE constraint on (studentId, bookId)
CREATE UNIQUE INDEX "ReadingSession_studentId_bookId_key" ON "ReadingSession"("studentId", "bookId");

-- Create indexes for filtering and queries
CREATE INDEX "ReadingSession_studentId_idx" ON "ReadingSession"("studentId");
CREATE INDEX "ReadingSession_bookId_idx" ON "ReadingSession"("bookId");
CREATE INDEX "ReadingSession_status_idx" ON "ReadingSession"("status");
