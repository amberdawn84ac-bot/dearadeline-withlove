# Declassified Documents Integration — Production Deployment Guide

**Last Updated:** April 2026
**Status:** Production-Ready

---

## Overview

This guide documents the deployment of the Declassified Documents integration for the Dear Adeline platform. The system integrates NARA, CIA FOIA, FBI Vault, Congressional Records, Federal Register, and DNSA documents into Hippocampus (pgvector) with full Witness Protocol verification, rate limiting, content filtering, and scheduled seeding.

---

## Prerequisites

### Database

1. **PostgreSQL 12+** with pgvector extension
   - Vector dimensions: 1536 (OpenAI embedding model)
   - Extension: `CREATE EXTENSION IF NOT EXISTS vector`

2. **Prisma Migrations Applied**
   - Migration: `20260403_add_hippocampus_unique_constraint`
   - Constraint: `(source_url, track)` uniqueness on `HippocampusDocument`
   - Verify:
     ```sql
     \d hippocampus_document
     -- Should show: CONSTRAINT hippocampus_document_source_url_track_key UNIQUE
     ```

3. **HippocampusDocument Table Schema**
   - Required columns: `id`, `source_url`, `source_type`, `track`, `chunk`, `embedding`, `similarity_score`, `citation_author`, `citation_year`, `citation_archive_name`
   - All embeddings must be dimension 1536 (OpenAI)

### API Keys & Credentials

```bash
# .env (adeline-brain)
ANTHROPIC_API_KEY=sk-ant-...                    # Claude API
OPENAI_API_KEY=sk-...                          # Embeddings + LLM
TAVILY_API_KEY=tvly-...                        # Deep web search (Rate limited: 10 req/day)
POSTGRES_DSN=postgresql://user:pass@host/db    # PostgreSQL connection
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io     # Neo4j Aura (or bolt://localhost:7687 for local)
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
UPSTASH_REDIS_REST_URL=https://...             # Optional: Serverless Redis
UPSTASH_REDIS_REST_TOKEN=...
```

### Python Dependencies

```bash
cd adeline-brain
pip install -r requirements.txt

# Verify key packages:
pip list | grep -E "APScheduler|pgvector|prisma|httpx|anthropic"
```

**Expected packages:**
- APScheduler 3.10.4+
- prisma 5.0+
- httpx 0.24+
- anthropic 0.7+

---

## Deployment Steps

### 1. Pre-deployment Verification

```bash
cd adeline-brain

# Verify schema is correct
npx prisma db push

# Verify migrations applied
npx prisma migrate status

# Check for pre-existing duplicates (should return 0 rows)
psql $POSTGRES_DSN <<EOF
SELECT source_url, track, COUNT(*)
FROM hippocampus_document
GROUP BY source_url, track
HAVING COUNT(*) > 1;
EOF

# Verify embeddings are dimension 1536
SELECT COUNT(*) FROM hippocampus_document
WHERE array_length(embedding, 1) != 1536;
# Expected: 0
```

### 2. Environment Validation

```bash
python -c "
import os
required = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'TAVILY_API_KEY', 'POSTGRES_DSN']
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f'❌ Missing env vars: {missing}')
    exit(1)
print('✓ All required env vars set')
"
```

### 3. Application Startup

```bash
# Start adeline-brain FastAPI server
uvicorn app.main:app --reload --port 8000

# Expected logs:
# [Scheduler] Started APScheduler with nightly declassified document seeding at 02:00 UTC
# INFO: Uvicorn running on http://0.0.0.0:8000
```

### 4. First-Run Seeding (Optional)

```bash
# Manually seed Hippocampus on first deployment (optional)
# Scheduler will run nightly at 2 AM UTC automatically
python -m app.scripts.seed_declassified_documents
```

---

## Monitoring & Observability

### Health Checks

```bash
# Check scheduler is running
curl http://localhost:8000/health

# Expected response:
# {"status": "ok", "scheduler": "running"}
```

### Key Monitoring Queries

```sql
-- Count documents by archive and track
SELECT archive_name, track, COUNT(*) as doc_count
FROM hippocampus_document
GROUP BY archive_name, track
ORDER BY doc_count DESC;

-- Check for duplicate attempts (should be 0)
SELECT COUNT(*) as duplicate_attempts
FROM (
  SELECT source_url, track, COUNT(*) as cnt
  FROM hippocampus_document
  GROUP BY source_url, track
  HAVING COUNT(*) > 1
) AS dups;

-- Check embedding quality (all should be 1536 dimensions)
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN array_length(embedding, 1) = 1536 THEN 1 END) as valid_embeddings,
  COUNT(CASE WHEN array_length(embedding, 1) != 1536 THEN 1 END) as invalid_embeddings
FROM hippocampus_document;

-- Check similarity scores (should be >= 0.0, <= 1.0)
SELECT
  COUNT(*) as total,
  MIN(similarity_score) as min_score,
  MAX(similarity_score) as max_score,
  AVG(similarity_score) as avg_score
FROM hippocampus_document;

-- Check for orphaned documents (no citation info)
SELECT COUNT(*) as orphaned
FROM hippocampus_document
WHERE citation_author IS NULL AND citation_year IS NULL;

-- Recent seeding activity (last 24 hours)
SELECT
  archive_name,
  COUNT(*) as documents_added,
  MAX(created_at) as last_seeded
FROM hippocampus_document
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY archive_name
ORDER BY last_seeded DESC;
```

### Logging

Structured logging includes context:
```
[student_id=abc track=TRUTH_HISTORY archive_name=NARA] Document seeded successfully
[archive_name=NARA] Search failed (attempt 1/3): ConnectionError. Retrying in 0.52s...
[Tavily] Rate limit reached; waiting for token refill...
[student_age=10] Document filtered: contains 'cointelpro' (requires age 14+)
```

### Alerts to Configure

1. **Scheduler failure:** If `/health` reports `scheduler: stopped`
2. **Rate limiter breach:** Watch logs for `Rate limit reached` patterns
3. **Database constraint violations:** Monitor `pg_stat_statements` for unique constraint errors
4. **High error rate:** Alert if error log lines exceed N per hour

---

## Rate Limiting

**Tavily API (Deep Web Search):**
- Max tokens: 10
- Refill rate: 0.5 tokens/sec
- Daily quota: ~10 searches/day
- Overages: Exponential backoff with jitter (0.5s, 1s, 2s, 4s...)

Monitor: Watch logs for `[Tavily] Rate limit reached` messages

---

## Content Filtering

Age-gated documents:
- **Ages 10-12:** No COINTELPRO, CIA assassination, torture, surveillance
- **Ages 13-14:** Surveillance allowed; no assassination/torture
- **Ages 15+:** All documents available (including sensitive)
- **No age specified:** All documents (assume adult access)

Sensitive keywords and minimum age gates are defined in `app/protocols/content_filter.py`.

---

## Scheduled Jobs

**Nightly Seeding Job:**
- **Time:** 2 AM UTC (02:00)
- **Frequency:** Daily
- **Function:** `seed_all_declassified_documents()`
- **Behavior:**
  - Seeds NARA, CIA FOIA, FBI Vault for TRUTH_HISTORY track
  - Seeds NARA, CIA FOIA, FBI Vault for JUSTICE_CHANGEMAKING track
  - Skips duplicates (enforced by database constraint)
  - Retries failed searches up to 3x with exponential backoff
  - Logs results with archive name and document count

**Verification:**
```bash
# Check if scheduler is registered and running
python -c "
from app.jobs.seed_scheduler import get_scheduler
sched = get_scheduler()
if sched and sched.running:
    jobs = sched.get_jobs()
    for job in jobs:
        print(f'Job: {job.name}, Next run: {job.next_run_time}')
else:
    print('❌ Scheduler not running')
"
```

---

## Rollback Procedure

### If Seeding Causes Issues

```bash
# 1. Disable scheduler (stop automatic seeding)
# Edit app/main.py, comment out:
#   await startup_seed_scheduler()

# 2. Verify scheduler is stopped
curl http://localhost:8000/health
# Expected: "scheduler": "stopped"

# 3. Identify problematic documents
SELECT * FROM hippocampus_document
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 50;

# 4. Delete problematic documents
DELETE FROM hippocampus_document
WHERE source_url = 'https://...' AND track = 'TRUTH_HISTORY';

# 5. Re-enable scheduler and redeploy
git revert HEAD~1  # or remove comment from app/main.py
uvicorn app.main:app --reload --port 8000
```

### If Database Constraint Causes Issues

```bash
# 1. Check for constraint violations
SELECT source_url, track, COUNT(*)
FROM hippocampus_document
GROUP BY source_url, track
HAVING COUNT(*) > 1;

# 2. Identify duplicates (keep most recent)
SELECT
  source_url, track, MAX(id) as most_recent_id,
  COUNT(*) as duplicate_count
FROM hippocampus_document
GROUP BY source_url, track
HAVING COUNT(*) > 1;

# 3. Delete older duplicates
DELETE FROM hippocampus_document
WHERE id NOT IN (
  SELECT MAX(id)
  FROM hippocampus_document
  GROUP BY source_url, track
);

# 4. Verify constraint is satisfied
SELECT COUNT(*) FROM hippocampus_document
GROUP BY source_url, track
HAVING COUNT(*) > 1;
# Expected: 0 rows
```

---

## Performance Tuning

### Index Optimization

```sql
-- Ensure embeddings are indexed for fast similarity search
CREATE INDEX IF NOT EXISTS idx_hippocampus_embedding
ON hippocampus_document
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index for track-based filtering
CREATE INDEX IF NOT EXISTS idx_hippocampus_track
ON hippocampus_document (track);

-- Index for uniqueness constraint (automatic in Prisma)
CREATE UNIQUE INDEX IF NOT EXISTS idx_hippocampus_url_track
ON hippocampus_document (source_url, track);
```

### Connection Pooling

```bash
# For high-concurrency scenarios, use PgBouncer
# Configure in .env:
POSTGRES_DSN=postgresql://user:pass@pgbouncer:6432/db?application_name=adeline
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'apscheduler'` | Missing dependency | `pip install APScheduler` |
| `UNIQUE constraint violation on (source_url, track)` | Duplicate document | Delete older duplicate, retry seed |
| `[Tavily] Rate limit reached` repeatedly | Too many searches | Check Tavily API quota, reduce daily seeding |
| `Embedding dimension mismatch` | Wrong model used | Ensure using OpenAI (1536 dims), not other models |
| `No documents returned` from search_witnesses | Hippocampus empty | Run seed script manually or wait for 2 AM UTC job |

---

## Support & Escalation

**For deployment issues:**
1. Check logs: `grep "\[ERROR\]" app.log`
2. Verify prerequisites: database, API keys, migrations
3. Run diagnostic: `python scripts/health_check.py`
4. Contact: Engineering team via GitHub issues

---

## Checklist for Production Readiness

- [ ] PostgreSQL running with pgvector extension
- [ ] All Prisma migrations applied
- [ ] Environment variables set and validated
- [ ] APScheduler installed in requirements.txt
- [ ] FastAPI app imports successfully
- [ ] Scheduler startup log appears on app boot
- [ ] First manual seed completes (or wait for 2 AM UTC)
- [ ] Monitoring queries return expected results
- [ ] Rate limiter tested (10 token limit enforced)
- [ ] Content filtering verified (age gates working)
- [ ] Rollback procedure documented and tested
