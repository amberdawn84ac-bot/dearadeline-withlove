-- Fix hippocampus deduplication key
--
-- The original UNIQUE(source_url, track) constraint allowed only ONE document
-- per track for any given source URL. This broke OAS seeding because all 3,043
-- standards share the same base URL (https://sde.ok.gov/oklahoma-academic-standards),
-- so only the first standard per track was stored and everything else was skipped.
--
-- New strategy: dedup by (source_url, chunk). Each chunk is unique content, so
-- multiple standards from the same source URL can coexist as separate rows.

-- Drop the over-broad constraint
DROP INDEX IF EXISTS "hippocampus_document_source_url_track_key";

-- Remove any rows that are exact duplicates (same source_url + chunk), keeping
-- the oldest row per pair to avoid primary-key conflicts on the new index.
DELETE FROM hippocampus_documents
WHERE id IN (
    SELECT id FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY source_url, chunk
                   ORDER BY created_at ASC
               ) AS rn
        FROM hippocampus_documents
    ) ranked
    WHERE rn > 1
);

-- Add the corrected unique index
CREATE UNIQUE INDEX "hippocampus_document_source_url_chunk_key"
    ON hippocampus_documents (source_url, md5(chunk));
