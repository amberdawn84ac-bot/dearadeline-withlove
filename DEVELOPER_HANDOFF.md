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
