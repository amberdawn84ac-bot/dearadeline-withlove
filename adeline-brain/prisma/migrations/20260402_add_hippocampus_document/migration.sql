-- CreateExtension (pgvector for embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- ── HippocampusDocument ────────────────────────────────────────────────────────
-- Stores embedded document chunks from primary sources, declassified docs, etc.
-- Used by Hippocampus (pgvector similarity search).
-- Constraint: (source_url, track) must be unique — prevents duplicate seeding of same source for same track.

CREATE TABLE "HippocampusDocument" (
    "id"                      TEXT          NOT NULL,
    "source_title"            TEXT          NOT NULL,
    "source_url"              TEXT          NOT NULL,
    "source_type"             TEXT          NOT NULL DEFAULT 'PRIMARY_SOURCE',
    "chunk"                   TEXT          NOT NULL,
    "embedding"               vector(1536)  NOT NULL,  -- OpenAI embedding dimension
    "citation_author"         TEXT          NOT NULL DEFAULT '',
    "citation_year"           INTEGER,
    "citation_archive_name"   TEXT          NOT NULL DEFAULT '',
    "track"                   TEXT          NOT NULL,
    "created_at"              TIMESTAMP(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at"              TIMESTAMP(3)  NOT NULL,

    CONSTRAINT "HippocampusDocument_pkey" PRIMARY KEY ("id")
);

-- Unique constraint: (source_url, track) pair must be unique
-- Prevents seeding the same source URL twice for the same track
CREATE UNIQUE INDEX "HippocampusDocument_source_url_track_key"
    ON "HippocampusDocument"("source_url", "track");

-- Index on track for filtering by curriculum track
CREATE INDEX "HippocampusDocument_track_idx"
    ON "HippocampusDocument"("track");

-- Index on source_url for deduplication checks
CREATE INDEX "HippocampusDocument_source_url_idx"
    ON "HippocampusDocument"("source_url");

-- Vector index for similarity search
CREATE INDEX "HippocampusDocument_embedding_idx"
    ON "HippocampusDocument" USING ivfflat ("embedding" vector_cosine_ops)
    WITH (lists = 100);
