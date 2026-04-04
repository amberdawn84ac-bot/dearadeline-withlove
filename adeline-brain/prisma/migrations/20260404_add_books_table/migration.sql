-- Add fields to Book model for Bookshelf v1 feature
-- Includes pgvector embedding for semantic search

-- Add new required fields to Book table
ALTER TABLE "Book" ADD COLUMN "source_url" TEXT;
ALTER TABLE "Book" ADD COLUMN "lexile_level" INTEGER;
ALTER TABLE "Book" ADD COLUMN "grade_band" TEXT;
ALTER TABLE "Book" ADD COLUMN "description" TEXT;
ALTER TABLE "Book" ADD COLUMN "track" TEXT NOT NULL DEFAULT 'ENGLISH_LITERATURE';
ALTER TABLE "Book" ADD COLUMN "embedding" vector(1536);

-- Add UNIQUE constraint on source_url to prevent duplicates
ALTER TABLE "Book" ADD CONSTRAINT "Book_source_url_unique" UNIQUE ("source_url");

-- Create indexes for common queries
CREATE INDEX "Book_track_idx" ON "Book"("track");
CREATE INDEX "Book_lexile_level_idx" ON "Book"("lexile_level");
CREATE INDEX "Book_sourceLibrary_idx" ON "Book"("sourceLibrary");

-- Create HNSW index for pgvector similarity search (cosine distance)
CREATE INDEX "Book_embedding_idx" ON "Book" USING hnsw ("embedding" vector_cosine_ops);
