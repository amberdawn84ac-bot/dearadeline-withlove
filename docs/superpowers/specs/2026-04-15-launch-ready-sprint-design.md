# Launch-Ready Sprint — Design Spec
**Date:** 2026-04-15
**Status:** Approved
**Scope:** Option B — stabilize Railway deployment, eliminate timeouts, add observability, canonical curriculum store, CI/CD gate

---

## Problem Statement

Railway is running a single Uvicorn worker with synchronous LLM calls in the request path. Long lessons time out. The rate limiter is in-memory and breaks across replicas. There is no error tracking, no deploy gate, and no curriculum caching — meaning every lesson re-generates from scratch, risking hallucination drift and values drift at scale. The genui callback endpoint has a confirmed NameError that makes it dead in production.

---

## Architecture Overview

Two processes share one Docker image on Railway:

- **web** — Gunicorn managing 4 Uvicorn workers, handles all HTTP
- **worker** — ARQ process, handles async lesson generation jobs

Redis is the shared broker (already in stack). Postgres and Neo4j are unchanged.

---

## Section 1 — Infrastructure & Workers

### entrypoint.sh
Replace:
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
With:
```
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:$PORT \
  --timeout 120 \
  --keep-alive 5
```

### Dockerfile (adeline-brain)
Two-stage build:
- `builder` stage: installs Python deps into `/venv`
- `runtime` stage: copies `/venv` + `app/` only — no pip, no build tools in prod image
- Non-root user `adeline` created and set via `USER adeline`
- `EXPOSE 8000` only

### railway.toml
```toml
[deploy]
healthcheckPath = "/health"
restartPolicyType = "ON_FAILURE"
```

### Health endpoint hardening
`GET /health` extended to check Redis ping and Postgres connectivity. Railway restarts the service if either dependency is down.

---

## Section 2 — Redis Rate Limiter + Session Cache

### Rate limiter
`slowapi` storage changed from `"memory://"` to `os.getenv("REDIS_URL")`. All replicas share one counter. Existing 120 req/min per IP limit unchanged.

### Session cache
Thin Redis cache in `redis_client.py`:
- Key: `student_state:{student_id}` — TTL 5 minutes
- Populated on first request per session
- Invalidated on `POST /journal/seal`
- Eliminates per-request DB round-trips for mastery scores, ZPD state, BKT params (~70% DB load reduction for active sessions)
- State is consistent across Railway replicas because it lives in Redis, not in-process

---

## Section 3 — Async Agent Orchestration (ARQ)

### Problem
`POST /lesson/generate` runs the full pipeline synchronously: embed → pgvector → Witness (history) → LLM → Registrar. Complex lessons take 15–45s. Railway timeout is 30s.

### Solution
ARQ task queue on top of existing Redis. Zero new infrastructure.

### Request flow
```
POST /lesson/generate
  → enqueue ARQ job
  → return { job_id, status: "queued" } immediately (< 200ms)

GET /lesson/status/{job_id}
  → { status: "queued" | "running" | "done" | "failed", result?: LessonResponse }

ARQ worker
  → picks job → checks canonical store (see Section 5)
  → runs full orchestrator only on cache miss
  → writes result to Redis (TTL 1hr)
  → frontend polling resolves
```

### Railway worker service
Same Docker image as web. Start command: `arq app.worker.WorkerSettings`
Same env vars. Same Redis URL.

### Frontend change (AdelineChatPanel.tsx)
1. `POST /lesson/generate` → receive `job_id`
2. Poll `GET /lesson/status/{job_id}` every 2s
3. Render lesson when `status === "done"` or show error on `"failed"`
Existing loading state in `AdelineChatPanel` is wired to the polling loop.

### What stays the same
All agent logic, orchestrator, Witness Protocol — untouched. ARQ wraps the existing `generate_lesson()` call.

---

## Section 4 — Observability

### Sentry
- `sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.1)` in `app/main.py`
- Captures all unhandled exceptions with stack trace, request context, student_id
- 10% trace sampling — enough visibility, no cost explosion
- Free tier (5k errors/month) sufficient for Founder phase

### Structured logging
Replace f-string log calls with JSON via `python-json-logger`. Every log line emits: `timestamp`, `level`, `student_id`, `lesson_id`, `track`, `agent`, `duration_ms`. Railway log viewer can filter by any field.

### genui.py NameError fix
Line 43: `get_current_user` → `get_current_user_id`. This is a confirmed runtime crash that makes the entire `/genui/callback` endpoint dead. Fix is one token.

### BKT callback fix
`genui.py` `onAnswer` handler: replace hardcoded `BKTParams(pL=0.5, pT=0.15, pS=0.05, pG=0.25)` with a fetch of the student's real BKT params from the session cache (Redis) or DB. Mastery updates are meaningless with hardcoded defaults.

---

## Section 5 — Canonical Lesson Store

### Architecture rationale
The canonical lesson is the **compiled, truth-verified curriculum artifact** for a topic. Like a compiler producing bytecode, the orchestrator runs once to produce a verified lesson. The ZPD adapter is the runtime renderer — it personalizes tone and scaffolding for each student without touching the source.

This makes Adeline's curriculum more reliable than any competitor using open-ended generation: the facts, sources, and worldview framing are fixed at canonical generation time and cannot drift.

### Witness Protocol scope
Only `TRUTH_HISTORY` and `JUSTICE_CHANGEMAKING` canonical lessons go through `evaluate_evidence()` at the 0.82 threshold. All other tracks: values-consistent, orchestrator-verified, no Witness gate. This matches the existing orchestrator routing.

### CanonicalLesson table (new Prisma migration)
```
CanonicalLesson {
  id            String   @id @default(cuid())
  track         String
  topic         String
  grade_band    String   // "K2" | "35" | "68" | "912"
  blocks        Json     // full LessonBlock array
  oas_standards Json
  agent_name    String
  generated_at  DateTime @default(now())
  refreshed_at  DateTime @updatedAt
  @@unique([track, topic, grade_band])
  @@index([track, grade_band])
}
```

### Orchestrator check (orchestrator.py)
```
generate_lesson() called
  → check Redis: canonical:{track}:{topic_normalized}:{grade_band}
    → HIT: skip Deep Thinking → jump to ZPD adapter
    → MISS: check Postgres CanonicalLesson
      → FOUND: write to Redis → jump to ZPD adapter
      → NOT FOUND: run full orchestrator → save to Postgres + Redis → adapt
```

Topic is normalized: lowercase, stripped punctuation, first 60 chars.

### ZPD Adapter endpoint

```
POST /lesson/deliver

Input:
  canonical_id: str
  student_id: str
  student_bkt_score: float    (fetched from Redis session cache)

Adapter prompt (injected server-side, not user-controlled):
  "You are an adapter. Below is a verified lesson. Do NOT change the facts,
   sources, or worldview framing. Rewrite the tone for {grade_band} reading
   level and increase hint density by {hint_multiplier}%."

hint_multiplier derived from student_bkt_score:
  score < 0.3  → +60% hints  (NOVICE)
  score < 0.6  → +40% hints  (DEVELOPING)
  score < 0.8  → +20% hints  (PROFICIENT)
  score >= 0.8 →  +0% hints  (ADVANCED — canonical as-is)

Output: PersonalizedLessonResponse
  canonical_id: str       ← always references source canonical lesson
  lesson_id: str          ← fresh UUID for this student's xAPI/CASE record
  blocks: [...]           ← adapted content, canonical structure preserved
  student_bkt_score: float
```

The adapter is **read-only on facts**: it cannot modify block content, swap evidence, change block type, or alter worldview framing. Tone and hint density only.

### Cache warmup (nightly ARQ job)
Runs at 2am. Queries all `CanonicalLesson` rows from Postgres, writes each to Redis. Ensures Redis is never cold after a restart or flush. Day 1 pre-generation: 64 Concept nodes × 4 grade bands = 256 canonical lessons generated before first student arrives.

### xAPI/CASE records
`canonical_id` is stored on every `StudentLesson` and `LearningRecord` row. Registrar still runs per-student on delivery, not on canonical generation.

---

## Section 6 — CI/CD + Test Gate

### GitHub Actions (.github/workflows/ci.yml)
Triggers on push to `main` and all PRs.

```
Job 1 — lint (30s)
  ruff check adeline-brain/
  npx eslint adeline-ui/src/

Job 2 — test-brain (2–3 min)
  pytest tests/ -x --tb=short
  Fails fast on first failure

Job 3 — deploy (runs only if 1 + 2 pass)
  railway up --service adeline-brain
  railway up --service adeline-worker
  railway up --service adeline-ui
```

### Pytest suite
| File | Covers |
|------|--------|
| `test_genui_callback.py` | NameError fix, all 4 event types |
| `test_bkt_engine.py` | BKT update with real params |
| `test_canonical_store.py` | Cache hit / miss / warmup logic |
| `test_witness_protocol.py` | evaluate_evidence() at 0.82 threshold, all 3 verdicts |
| `test_rate_limiter.py` | Redis-backed limiter behavior |
| `test_orchestrator_routing.py` | Each track routes to correct agent |

Tests use real test Redis and Postgres instances via `pytest-asyncio`. No mocking of DB or Redis — that's what catches the bugs mocks miss.

**requirements.txt additions:** `pytest`, `pytest-asyncio`, `pytest-httpx`, `ruff`

---

## Section 7 — Security Hardening (Production Only)

### Docker
- Multi-stage build (see Section 1)
- Non-root user `adeline` (see Section 1)

### CORS
```python
allow_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
```
Railway env var: `CORS_ORIGINS=https://dearadeline.co,https://www.dearadeline.co`

### Git pre-commit hook
Rejects commits containing `sk-`, `AIza`, or `postgresql://`. Blocks secrets from reaching Railway via a bad push.

---

## Files Created / Modified

### adeline-brain
| File | Change |
|------|--------|
| `Dockerfile` | Multi-stage, non-root user |
| `entrypoint.sh` | Gunicorn replacing bare uvicorn |
| `app/main.py` | Sentry init, JSON logging config |
| `app/api/genui.py` | Fix NameError, wire real BKT params |
| `app/api/lessons.py` | ARQ enqueue, `/lesson/status/{job_id}`, `/lesson/deliver` |
| `app/worker.py` | ARQ WorkerSettings + job definitions (new) |
| `app/connections/redis_client.py` | Session cache methods, rate limiter storage |
| `app/agents/orchestrator.py` | Canonical store check before Deep Thinking |
| `app/algorithms/zpd_engine.py` | No change — pure computation |
| `prisma/schema.prisma` | CanonicalLesson model |
| `prisma/migrations/` | New migration for CanonicalLesson |
| `requirements.txt` | Add arq, sentry-sdk[fastapi], python-json-logger, gunicorn, pytest stack |
| `railway.toml` | healthcheckPath, restartPolicyType |

### adeline-ui
| File | Change |
|------|--------|
| `src/lib/brain-client.ts` | `generateLesson` returns job_id, add `getLessonStatus` |
| `src/components/AdelineChatPanel.tsx` | Polling loop replacing single await |

### Root
| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Full CI/CD pipeline (new) |
| `.git/hooks/pre-commit` | Secret scanning hook (new) |
| `tests/` | 6 new test files |

---

## Non-Goals (explicitly out of scope)

- OAuth / identity provider (post-Founder phase)
- K8s / Terraform
- Data warehouse (Snowflake/BigQuery)
- A11y / i18n
- Neo4j sharding
- Local dev Docker Compose changes
