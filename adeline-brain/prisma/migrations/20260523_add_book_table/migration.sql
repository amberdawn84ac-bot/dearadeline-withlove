-- Add Book and ReadingSession tables for literature tracking

-- Create Book table
CREATE TABLE IF NOT EXISTS "Book" (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    description TEXT,
    track "Track" NOT NULL,
    "gradeBand" TEXT,
    "lexileLevel" INTEGER,
    "coverImageUrl" TEXT,
    "sourceUrl" TEXT,
    isbn TEXT,
    "totalPages" INTEGER,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for Book
CREATE INDEX IF NOT EXISTS "Book_track_idx" ON "Book"(track);
CREATE INDEX IF NOT EXISTS "Book_title_idx" ON "Book"(title);

-- Create ReadingSession table
CREATE TABLE IF NOT EXISTS "ReadingSession" (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
    "studentId" TEXT NOT NULL,
    "bookId" TEXT NOT NULL REFERENCES "Book"(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'reading',
    "currentLocation" TEXT,
    "pagesRead" INTEGER DEFAULT 0,
    "totalPages" INTEGER,
    "minutesRead" INTEGER DEFAULT 0,
    "startedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "completedAt" TIMESTAMP WITH TIME ZONE,
    UNIQUE("studentId", "bookId")
);

-- Create indexes for ReadingSession
CREATE INDEX IF NOT EXISTS "ReadingSession_studentId_idx" ON "ReadingSession"("studentId");
CREATE INDEX IF NOT EXISTS "ReadingSession_bookId_idx" ON "ReadingSession"("bookId");

-- Enable RLS on both tables
ALTER TABLE "Book" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ReadingSession" ENABLE ROW LEVEL SECURITY;

-- RLS policies for Book (readable by all, writable by admin)
CREATE POLICY "Book_select_all" ON "Book" FOR SELECT USING (true);
CREATE POLICY "Book_insert_admin" ON "Book" FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Book_update_admin" ON "Book" FOR UPDATE USING (auth.role() = 'authenticated');

-- RLS policies for ReadingSession (students see their own, admins see all)
CREATE POLICY "ReadingSession_select_own" ON "ReadingSession" FOR SELECT USING (
    auth.uid()::text = "studentId" OR auth.role() = 'service_role'
);
CREATE POLICY "ReadingSession_insert_own" ON "ReadingSession" FOR INSERT WITH CHECK (
    auth.uid()::text = "studentId" OR auth.role() = 'service_role'
);
CREATE POLICY "ReadingSession_update_own" ON "ReadingSession" FOR UPDATE USING (
    auth.uid()::text = "studentId" OR auth.role() = 'service_role'
);
