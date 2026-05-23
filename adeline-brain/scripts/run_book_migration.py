"""Run Book table migration directly using asyncpg."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_db_conn

MIGRATION_SQL = """
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
"""

async def migrate():
    print("Running Book table migration...")
    conn = await get_db_conn()
    try:
        await conn.execute(MIGRATION_SQL)
        print("✅ Book and ReadingSession tables created successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
