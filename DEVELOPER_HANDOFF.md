# Dear Adeline 2.0 — Developer Handoff

**Architecture:** Truth-First K-12 AI Mentor · Oklahoma
**Date:** 2026-03-27
**Status:** MVP Complete — Brain + UI wired, JWT auth in production, DB connected

---

## Services

| Service | Port | Tech |
|---------|------|------|
| `adeline-ui` | 3000 | Next.js 14 + Tailwind |
| `adeline-brain` | 8000 | FastAPI + LangGraph |
| Postgres (Hippocampus + Journal) | 5432 | pgvector |
| Neo4j (GraphRAG) | 7687 (bolt) / 7474 (browser) | Neo4j |

Start everything: `docker-compose up --build`

---

## API Routes

### Health (no auth required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service alive check |
| GET | `/health/truth` | Runs a Douglass query against Hippocampus, returns score + verdict |
| GET | `/lessons/health` | Hippocampus document count |
| GET | `/tracks` | Returns all 10 Track IDs and labels |

### Lessons (requires `X-User-Role: STUDENT` or `ADMIN`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/lessons/generate` | Generate a lesson from a topic query |

**Request body:**
```json
{
  "student_id": "string",
  "track": "TRUTH_HISTORY",
  "topic": "string",
  "is_homestead": false,
  "grade_level": "8"
}
```

### Journal (requires `X-User-Role: STUDENT` or `ADMIN`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/journal/seal` | Seal a completed lesson; upserts Postgres + fires Neo4j Mastery |
| GET | `/journal/progress/{student_id}` | Track progress counts `{ TRUTH_HISTORY: 3, ... }` |
| GET | `/journal/recent/{student_id}` | Last 10 sealed lessons with timestamps |

**Seal request body:**
```json
{
  "student_id": "string",
  "lesson_id": "string",
  "track": "TRUTH_HISTORY",
  "completed_blocks": 3,
  "oas_standards": [{ "standard_id": "OK.US.H.5.4", "text": "...", "grade": 8 }]
}
```

### Opportunities (requires `X-User-Role: ADMIN`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/opportunities` | Oklahoma local learning opportunities |

---

## The Witness Protocol (0.82 Truth Gate)

Every lesson block is evaluated by cosine similarity against the Hippocampus corpus:

```
similarity_score >= 0.82  →  verdict: VERIFIED           →  PRIMARY_SOURCE block + Verified Seal
similarity_score >= 0.65  →  verdict: INVESTIGATING      →  SearchWitnesses fallback
similarity_score  < 0.65  →  verdict: ARCHIVE_SILENT     →  RESEARCH_MISSION block assigned
```

- Threshold constant: `TRUTH_THRESHOLD = 0.82` in `app/protocols/witness.py`
- Health check: 3-tier (VERIFIED >= 0.82, INVESTIGATING >= 0.65, ARCHIVE_SILENT < 0.65)
- Hippocampus table: `hippocampus_documents` (pgvector, 1536-dim embeddings)
- Embedding model: `text-embedding-3-small` (OpenAI)

---

## Neo4j Graph Schema

### Node types
| Label | Key property | Description |
|-------|-------------|-------------|
| `Student` | `id` | Student user (student_id from lesson request) |
| `OASStandard` | `id` | Oklahoma Academic Standard (e.g. `OK.US.H.5.4`) |
| `Track` | `name` | One of the 10 constitutional tracks |

### Relationship types
| Relationship | From → To | Created when |
|-------------|-----------|-------------|
| `ENROLLED_IN` | Student → Track | First lesson sealed on a track |
| `MASTERED` | Student → OASStandard | Lesson sealed with OAS standards |
| `MAPS_TO_TRACK` | OASStandard → Track | Standard upserted during seal |

### Mastery query example
```cypher
MATCH (s:Student {id: "demo-student-001"})-[:MASTERED]->(std:OASStandard)
RETURN std.id, std.grade, std.track
ORDER BY std.grade
```

---

## Database Tables

### `hippocampus_documents` (pgvector)
Stores verified source document chunks and their embeddings for semantic search.

### `student_journal`
Tracks sealed lessons per student.

| Column | Type | Notes |
|--------|------|-------|
| `student_id` | varchar | PK part 1 |
| `lesson_id` | varchar | PK part 2 |
| `track` | varchar | One of 10 track IDs |
| `completed_blocks` | int | Count of VERIFIED blocks at seal time |
| `sealed_at` | timestamptz | Upserted on each seal |

---

## Auth (Supabase JWT)

**Production** (`SUPABASE_JWT_SECRET` set): All protected routes verify the `Authorization: Bearer <token>` header as a Supabase-issued JWT (HS256, audience `authenticated`). User role is extracted from `app_metadata.role`.

**Development** (`SUPABASE_JWT_SECRET` not set): Falls back to header-based auth (`X-User-Role` + `X-User-Id`) with a logged warning. This fallback is blocked if `ADELINE_ENV=production`.

Rate limiting: 120 req/min per IP via slowapi middleware.

---

## Production Secrets

The following environment variables must be set in production. See `.env.example` for reference.

| Variable | Description | Service |
|----------|-------------|---------|
| `SUPABASE_JWT_SECRET` | Supabase JWT signing secret for auth verification | adeline-brain |
| `OPENAI_API_KEY` | OpenAI API key for embeddings and LLM calls | adeline-brain |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude LLM calls | adeline-brain |
| `TAVILY_API_KEY` | Tavily API key for deep web search | adeline-brain |
| `NEO4J_URI` | Neo4j connection URI (e.g., `bolt://localhost:7687`) | adeline-brain |
| `NEO4J_USER` | Neo4j username | adeline-brain |
| `NEO4J_PASSWORD` | Neo4j password | adeline-brain |
| `NEO4J_DATABASE` | Neo4j database name (optional) | adeline-brain |
| `NEO4J_MAX_POOL_SIZE` | Neo4j connection pool max size (default: 50) | adeline-brain |
| `NEO4J_ACQUIRE_TIMEOUT` | Neo4j connection acquisition timeout in seconds (default: 30) | adeline-brain |
| `NEO4J_QUERY_TIMEOUT` | Neo4j query timeout in seconds (default: 10) | adeline-brain |
| `REDIS_URL` | Redis connection URL for canonical store cache | adeline-brain |
| `ADMIN_REVIEW_WEBHOOK_URL` | Webhook URL for HITL canonical review notifications (optional) | adeline-brain |
| `ADELINE_ENV` | Environment: `production` or `development` | adeline-brain |

**Security notes:**
- Never commit secrets to git. Use Railway environment variables or a secrets manager.
- Rotate API keys regularly.
- Use least-privilege IAM roles for database access.

---

## Cloud Scaling

### Neo4j Knowledge Graph

Neo4j is configured for concurrent student loads via connection pooling and query timeouts:

- **Connection pool size**: Configured via `NEO4J_MAX_POOL_SIZE` (default: 50). Adjust based on expected concurrent students. For 100 concurrent students, start with 50-100 connections.
- **Connection acquisition timeout**: `NEO4J_ACQUIRE_TIMEOUT` (default: 30 seconds). Prevents indefinite blocking when pool is exhausted.
- **Query timeout**: `NEO4J_QUERY_TIMEOUT` (default: 10 seconds). Prevents runaway queries from blocking the pool.
- **Indexing**: Critical indexes are in place for ZPD queries:
  - `SpacedRepetitionCard_studentId_track_idx` on `(studentId, track)` for proficiency lookups

**Scaling guidance:**
- Monitor connection pool exhaustion in logs. If seeing "Connection acquisition timeout" errors, increase `NEO4J_MAX_POOL_SIZE`.
- For high traffic (> 500 concurrent students), consider a dedicated Neo4j instance with vertical scaling (more CPU/RAM) or horizontal scaling (Neo4j cluster).

### Railway Deployment

Railway auto-scales based on traffic. Key considerations:

- **adeline-brain**: CPU/memory limits in Railway. Monitor for OOM errors during heavy LLM calls.
- **Postgres**: Railway managed Postgres with pgvector extension. Connection pooling is handled by Railway.
- **Redis**: Use Railway's Redis service for canonical store cache. Set `REDIS_URL` accordingly.

**Environment variables:** Set all secrets in Railway project settings, not in `.env` files.

### Redis Cache

Redis is used for canonical lesson caching (fast retrieval, reduced DB load):

- **TTL**: Canonicals are cached with a default TTL. Adjust based on content freshness requirements.
- **Connection**: Single connection pool is sufficient for most loads. Redis is highly performant.

### Rate Limiting

The system uses token bucket rate limiting for external APIs:

- **Tavily API**: 10 tokens max, 0.5 tokens/second refill (~10 API calls with gradual recovery). Concurrent calls capped at 5 via `asyncio.Semaphore`.
- **Lesson generation**: 20 lessons/hour per IP via slowapi middleware.

**Scaling guidance:**
- Monitor Tavily rate limit errors. If hitting 429s frequently, increase token bucket size or reduce concurrent semaphore.
- For production with high student volume, consider a queue system (e.g., Celery + Redis) for lesson generation to smooth burst loads.

---

## Database Migrations

Database schema changes are managed through a single migration file: `prisma/migrations/apply_all.sql`.

### Migration Workflow

1. **Create new migration**: Add schema changes to a new dated migration file in `prisma/migrations/YYYYMMDD_description/migration.sql`.
2. **Append to apply_all.sql**: Copy the new migration's SQL statements into `prisma/migrations/apply_all.sql` with a comment header indicating the date and purpose.
3. **Apply migrations**: Run `apply_all.sql` against the production database. This file is the single source of truth for the complete schema.

### Example: 2026-04-14 CanonicalLesson HITL Approval Columns

```sql
-- ── 2026-04-14: CanonicalLesson HITL approval columns ────────────────────────
ALTER TABLE "CanonicalLesson"
  ADD COLUMN IF NOT EXISTS "pendingApproval" BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS "needsReviewReason" TEXT;

CREATE INDEX IF NOT EXISTS "CanonicalLesson_pending_idx"
  ON "CanonicalLesson" ("pendingApproval")
  WHERE "pendingApproval" = TRUE;
```

### Important Notes

- **Always use `IF NOT EXISTS`** for columns and indexes to make migrations idempotent and safe to re-run.
- **Add indexes** for columns used in WHERE clauses (e.g., `studentId`, `track` for ZPD queries).
- **Document the purpose** with comment headers in `apply_all.sql` for future maintainability.
- **Test locally** before applying to production: `psql $DATABASE_URL -f prisma/migrations/apply_all.sql`.

### Current Schema Highlights

- **CanonicalLesson**: Stores canonical lesson templates with HITL approval columns (`pendingApproval`, `needsReviewReason`, `lastApprovedAt`, `approvedBy`).
- **SpacedRepetitionCard**: Tracks student proficiency per concept with compound index on `(studentId, track)` for ZPD queries.
- **hippocampus_documents**: pgvector table for semantic search (1536-dim embeddings).

---

## UI Pages

| URL | Description |
|-----|-------------|
| `localhost:3000` | Landing page — 8-Track Constitution + Witness Protocol note |
| `localhost:3000/lesson` | Live lesson engine — query → generate → seal |
| `localhost:3000/lesson/douglass` | Static showcase — Frederick Douglass (3 Verified Seals) |
| `localhost:3000/dashboard` | 8-Track progress circles + recent activity |

---

## What Still Needs Real Data

- [ ] Load curated source documents into Hippocampus: `python scripts/seed_curriculum.py`
- [ ] Set `OPENAI_API_KEY` in `.env`
- [ ] Replace `demo-student-001` with real student auth/session
- [ ] Build Neo4j OAS Standards graph: `python scripts/seed_knowledge_graph.py`
- [x] ~~Add JWT auth to replace header stub~~ (done — Supabase JWT via `middleware.py`)

---

## Founder Alpha — Invite Codes

**Status:** `InviteCode` table is seeded and ready. 50 Founder codes (`ADEL-XXXX-2026`) live in Postgres.

**To generate / regenerate codes:**
```bash
cd adeline-brain
python scripts/generate_founder_codes.py
```

**Schema** (`prisma/migrations/20260327_add_invite_codes/migration.sql`):

| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID) | PK |
| `code` | TEXT | Unique — format `ADEL-XXXX-2026` |
| `isUsed` | BOOLEAN | Default `false` |
| `claimedByEmail` | TEXT | Nullable — set at redemption |
| `createdAt` | TIMESTAMP | Auto |

**Next step — POST /auth/register:**
Wire invite code redemption into the Supabase sign-up flow:
1. Validate `invite_code` is present, exists, and `isUsed = false`
2. Set `isUsed = true`, `claimedByEmail = new user's email`
3. Create Supabase user (JWT issued by Supabase) and `User` row
