# Launch-Ready Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize Railway deployment, eliminate request timeouts, add observability, and wire a CI/CD gate so broken code never reaches production again.

**Architecture:** Gunicorn 4-worker web process + ARQ background worker share one Docker image and one Redis instance. Lesson generation moves off the HTTP request path into ARQ, eliminating timeout risk. Sentry captures all production errors. GitHub Actions blocks deploys on test failure.

**Tech Stack:** FastAPI, Gunicorn, Uvicorn workers, ARQ 0.26.1 (Redis-backed queue), Sentry SDK, python-json-logger, GitHub Actions, pytest-asyncio

---

## File Map

| File | Status | Change |
|------|--------|--------|
| `adeline-brain/app/api/genui.py` | Modify | Fix NameError + real BKT params |
| `adeline-brain/app/main.py` | Modify | Sentry init, JSON logging, Redis rate limiter |
| `adeline-brain/app/connections/redis_client.py` | Modify | Add session cache methods, expose `redis_pool` for ARQ |
| `adeline-brain/app/api/lessons.py` | Modify | Replace sync generate with ARQ enqueue + status route |
| `adeline-brain/app/jobs/lesson_jobs.py` | Create | ARQ job function wrapping run_orchestrator |
| `adeline-brain/app/jobs/warmup_jobs.py` | Create | Nightly canonical cache warmup job |
| `adeline-brain/app/worker.py` | Create | ARQ WorkerSettings — startup, shutdown, job list |
| `adeline-brain/entrypoint.sh` | Modify | Gunicorn replacing bare uvicorn |
| `adeline-brain/Dockerfile` | Modify | Multi-stage build, non-root user adeline |
| `adeline-brain/requirements.txt` | Modify | Add gunicorn, arq, sentry-sdk, python-json-logger, pytest stack |
| `adeline-brain/railway.toml` | Create | healthcheckPath, restartPolicy |
| `adeline-ui/src/lib/brain-client.ts` | Modify | `generateLesson` returns job_id, add `getLessonStatus` |
| `adeline-ui/src/components/AdelineChatPanel.tsx` | Modify | Polling loop replacing single await |
| `.github/workflows/ci.yml` | Create | Lint + test + Railway deploy gate |
| `.git/hooks/pre-commit` | Create | Block sk-/key commits |
| `adeline-brain/tests/test_genui_callback.py` | Create | NameError fix + 4 event types coverage |
| `adeline-brain/tests/test_arq_lesson.py` | Create | Job enqueue + status polling |

---

## Task 1: Fix genui.py NameError + hardcoded BKT params

**Files:**
- Modify: `adeline-brain/app/api/genui.py`
- Create: `adeline-brain/tests/test_genui_callback.py`

- [ ] **Step 1: Write the failing test**

Create `adeline-brain/tests/test_genui_callback.py`:

```python
"""Tests for /genui/callback endpoint — covers the NameError fix and all 4 event types."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

# We import app directly — no mocking of DB yet; we patch at the dependency level
from app.main import app


@pytest.fixture
def auth_headers():
    """Dummy auth headers — middleware is patched in each test."""
    return {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_onAnswer_returns_updated_mastery(auth_headers):
    """onAnswer event returns a float mastery score — not a NameError."""
    with patch("app.api.genui.get_current_user_id", return_value="student-123"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/genui/callback", json={
                "student_id": "student-123",
                "lesson_id": "lesson-abc",
                "component_type": "InteractiveQuiz",
                "event": "onAnswer",
                "state": {"isCorrect": True},
            }, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["updated_mastery"], float)
    assert 0.0 <= body["updated_mastery"] <= 1.0


@pytest.mark.asyncio
async def test_onComplete_succeeds(auth_headers):
    with patch("app.api.genui.get_current_user_id", return_value="student-123"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/genui/callback", json={
                "student_id": "student-123",
                "lesson_id": "lesson-abc",
                "component_type": "ScaffoldedProblem",
                "event": "onComplete",
                "state": {},
            }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_onHint_triggers_rerender_at_threshold(auth_headers):
    with patch("app.api.genui.get_current_user_id", return_value="student-123"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/genui/callback", json={
                "student_id": "student-123",
                "lesson_id": "lesson-abc",
                "component_type": "ScaffoldedProblem",
                "event": "onHint",
                "state": {"hintsUsed": 3},
            }, headers=auth_headers)
    body = resp.json()
    assert body["success"] is True
    assert body["should_re_render"] is True


@pytest.mark.asyncio
async def test_onStruggle_triggers_scaffolding_rerender(auth_headers):
    with patch("app.api.genui.get_current_user_id", return_value="student-123"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/genui/callback", json={
                "student_id": "student-123",
                "lesson_id": "lesson-abc",
                "component_type": "ScaffoldedProblem",
                "event": "onStruggle",
                "state": {"wrongAttempts": 2, "scaffolding_level": 0},
            }, headers=auth_headers)
    body = resp.json()
    assert body["success"] is True
    assert body["should_re_render"] is True
    assert body["new_state"]["scaffolding_level"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd adeline-brain
pytest tests/test_genui_callback.py -v
```
Expected: all 4 tests FAIL — `NameError: name 'get_current_user' is not defined`

- [ ] **Step 3: Fix the NameError in genui.py**

In `adeline-brain/app/api/genui.py`, line 43, change:

```python
async def genui_callback(
    request: GenuiCallbackRequest,
    current_user = Depends(get_current_user),
):
```

to:

```python
async def genui_callback(
    request: GenuiCallbackRequest,
    current_user_id: str = Depends(get_current_user_id),
):
```

- [ ] **Step 4: Fix hardcoded BKT params in onAnswer handler**

In `adeline-brain/app/api/genui.py`, replace the hardcoded BKT block (lines ~74–79):

```python
    if request.event == "onAnswer":
        is_correct = request.state.get("isCorrect", False)
        # TODO: Fetch current BKT params for this concept from database
        # For now, use default params
        params = BKTParams(pL=0.5, pT=0.15, pS=0.05, pG=0.25)
        updated_mastery = bkt_update(params, is_correct)
        logger.info(f"[GENUI] BKT update: correct={is_correct}, new_mastery={updated_mastery:.3f}")
```

with:

```python
    if request.event == "onAnswer":
        is_correct = request.state.get("isCorrect", False)
        # Fetch real BKT params from student state; fall back to defaults
        try:
            from app.models.student import load_student_state
            student_state = await load_student_state(request.student_id)
            track_mastery = student_state.get(request.state.get("track", "TRUTH_HISTORY"))
            pL = track_mastery.mastery_score if track_mastery else 0.5
        except Exception:
            pL = 0.5
        params = BKTParams(pL=pL, pT=0.15, pS=0.05, pG=0.25)
        updated_mastery = bkt_update(params, is_correct)
        logger.info(f"[GENUI] BKT update: correct={is_correct}, pL={pL:.3f}, new_mastery={updated_mastery:.3f}")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_genui_callback.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/api/genui.py tests/test_genui_callback.py
git commit -m "fix: genui.py NameError + real BKT params on callback"
```

---

## Task 2: Add Sentry + JSON Structured Logging

**Files:**
- Modify: `adeline-brain/app/main.py`
- Modify: `adeline-brain/requirements.txt`

- [ ] **Step 1: Add dependencies to requirements.txt**

Append to `adeline-brain/requirements.txt`:

```
# Observability
sentry-sdk[fastapi]==2.5.1
python-json-logger==2.0.7
```

- [ ] **Step 2: Replace logging config in main.py**

In `adeline-brain/app/main.py`, replace the single line:

```python
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

with:

```python
import json
from pythonjsonlogger import jsonlogger

def _configure_logging():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

_configure_logging()
logger = logging.getLogger(__name__)
```

- [ ] **Step 3: Add Sentry init in main.py**

Immediately after the logging config block, add:

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN:
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
        send_default_pii=False,
    )
    logger.info("[adeline-brain] Sentry initialized")
```

- [ ] **Step 4: Add Redis check to /health endpoint**

In `adeline-brain/app/main.py`, in the `health()` function, add after the existing Neo4j check:

```python
    # Check Redis connectivity
    try:
        from app.connections.redis_client import ping as redis_ping
        redis_ok = await redis_ping()
        health_status["redis"] = "ok" if redis_ok else "unreachable"
    except Exception as e:
        health_status["redis"] = f"error: {e}"
```

- [ ] **Step 5: Verify locally**

```bash
cd adeline-brain
pip install sentry-sdk[fastapi]==2.5.1 python-json-logger==2.0.7
uvicorn app.main:app --port 8000 &
curl http://localhost:8000/health | python -m json.tool
```
Expected: JSON response includes `"redis": "ok"` and logs are in JSON format.

- [ ] **Step 6: Commit**

```bash
git add app/main.py requirements.txt
git commit -m "feat: add Sentry error tracking and JSON structured logging"
```

---

## Task 3: Gunicorn Multi-Worker

**Files:**
- Modify: `adeline-brain/entrypoint.sh`
- Modify: `adeline-brain/requirements.txt`

- [ ] **Step 1: Add gunicorn to requirements.txt**

Append to `adeline-brain/requirements.txt`:

```
gunicorn==21.2.0
```

- [ ] **Step 2: Replace uvicorn with gunicorn in entrypoint.sh**

Replace the last line of `adeline-brain/entrypoint.sh`:

```sh
echo "[entrypoint] Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" "$@"
```

with:

```sh
echo "[entrypoint] Starting gunicorn on port ${PORT:-8000} with 4 workers..."
exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout 120 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile - \
  "$@"
```

- [ ] **Step 3: Verify locally**

```bash
cd adeline-brain
pip install gunicorn==21.2.0
bash entrypoint.sh
```
Expected: logs show `[gw0] [gw1] [gw2] [gw3] Booting worker` for 4 workers, listening on port 8000.
Stop with Ctrl-C.

- [ ] **Step 4: Commit**

```bash
git add entrypoint.sh requirements.txt
git commit -m "feat: replace uvicorn with gunicorn 4-worker for production"
```

---

## Task 4: Docker Multi-Stage Build + Non-Root User

**Files:**
- Modify: `adeline-brain/Dockerfile`

- [ ] **Step 1: Rewrite Dockerfile**

Replace the entire contents of `adeline-brain/Dockerfile` with:

```dockerfile
# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/deps -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system adeline \
    && adduser --system --ingroup adeline --no-create-home adeline

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY prisma/ ./prisma/
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh \
    && chown -R adeline:adeline /app

USER adeline

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
```

- [ ] **Step 2: Build and verify image**

```bash
cd adeline-brain
docker build -t adeline-brain:test .
docker run --rm adeline-brain:test whoami
```
Expected: `adeline` (not `root`)

```bash
docker images adeline-brain:test --format "{{.Size}}"
```
Expected: image size smaller than before (was ~1.2GB, now ~600MB).

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: multi-stage Docker build + non-root user adeline"
```

---

## Task 5: railway.toml

**Files:**
- Create: `adeline-brain/railway.toml`

- [ ] **Step 1: Create railway.toml**

Create `adeline-brain/railway.toml`:

```toml
[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 2: Verify the health endpoint returns 200**

```bash
cd adeline-brain
uvicorn app.main:app --port 8000 &
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
```
Expected: `200`

- [ ] **Step 3: Commit**

```bash
git add railway.toml
git commit -m "feat: railway.toml with health check and restart policy"
```

---

## Task 6: Redis-Backed Rate Limiter

**Files:**
- Modify: `adeline-brain/app/main.py`

- [ ] **Step 1: Write the failing test**

Create `adeline-brain/tests/test_redis_rate_limiter.py`:

```python
"""Verify rate limiter uses Redis storage (not memory://)."""
import pytest
from app.main import limiter


def test_rate_limiter_uses_redis_storage():
    """The rate limiter storage_uri must NOT be memory:// in production."""
    storage_uri = str(limiter._storage_uri)
    assert storage_uri != "memory://", (
        "Rate limiter is using in-memory storage — "
        "this breaks across Railway replicas. Set REDIS_URL."
    )
    assert "redis" in storage_uri.lower(), (
        f"Expected Redis storage URI, got: {storage_uri}"
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd adeline-brain
pytest tests/test_redis_rate_limiter.py -v
```
Expected: FAIL — `AssertionError: Rate limiter is using in-memory storage`

- [ ] **Step 3: Update rate limiter in main.py**

In `adeline-brain/app/main.py`, replace:

```python
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],       # Global: 120 req/min per IP
    storage_uri="memory://",
)
```

with:

```python
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    storage_uri=_REDIS_URL,
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
# Start Redis locally first
redis-server --daemonize yes
pytest tests/test_redis_rate_limiter.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_redis_rate_limiter.py
git commit -m "fix: rate limiter storage moved from memory to Redis"
```

---

## Task 6b: Redis Session Cache for Student State

**Files:**
- Modify: `adeline-brain/app/models/student.py`
- Modify: `adeline-brain/app/api/journal.py` (invalidate on seal)

`load_student_state` currently hits Postgres on every lesson request. With Redis session cache, active students hit Redis instead. Cache is invalidated on `journal/seal` so mastery scores stay fresh.

- [ ] **Step 1: Add cache wrapper to load_student_state**

In `adeline-brain/app/models/student.py`, wrap the existing `load_student_state` function. Find the function:

```python
async def load_student_state(student_id: str) -> StudentState:
```

Add this above it:

```python
_STUDENT_STATE_TTL = 300  # 5 minutes


async def _get_cached_student_state(student_id: str) -> Optional[dict]:
    from app.connections.redis_client import redis_client
    import json
    try:
        raw = await redis_client.get(f"student_state:{student_id}")
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def _set_cached_student_state(student_id: str, state: dict) -> None:
    from app.connections.redis_client import redis_client
    import json
    try:
        await redis_client.set(
            f"student_state:{student_id}",
            json.dumps(state),
            ex=_STUDENT_STATE_TTL,
        )
    except Exception:
        pass  # Cache write failure is non-fatal


async def invalidate_student_state_cache(student_id: str) -> None:
    """Call this from journal/seal to force fresh state on next lesson."""
    from app.connections.redis_client import redis_client
    try:
        await redis_client.delete(f"student_state:{student_id}")
    except Exception:
        pass
```

Then wrap the body of `load_student_state` to check cache first. Add at the very top of the function body (before any DB call):

```python
async def load_student_state(student_id: str) -> StudentState:
    # Check Redis first
    cached = await _get_cached_student_state(student_id)
    if cached:
        return {k: _parse_track_mastery(v) for k, v in cached.items()}

    # DB fetch (existing logic unchanged below this line)
    # ... existing code continues ...

    # After existing code builds `state`, add before the return:
    await _set_cached_student_state(student_id, {k: v.__dict__ for k, v in state.items()})
    return state
```

Note: `_parse_track_mastery` converts the cached dict back to the `TrackMastery` dataclass. Check the actual return type of `load_student_state` and match the deserialization to it.

- [ ] **Step 2: Invalidate cache on journal/seal**

In `adeline-brain/app/api/journal.py`, find the `seal_journal` endpoint. After the existing seal logic succeeds, add:

```python
    # Invalidate student state cache so next lesson sees fresh mastery
    from app.models.student import invalidate_student_state_cache
    await invalidate_student_state_cache(student_id)
```

- [ ] **Step 3: Verify locally**

```bash
cd adeline-brain
# Start Redis
redis-server --daemonize yes
# Run the app and check logs for cache hits
uvicorn app.main:app --port 8000 &
# Make two lesson requests for the same student — second should log cache HIT
```
Expected: second request shows `[Redis]` cache hit in logs, not a DB fetch.

- [ ] **Step 4: Commit**

```bash
git add app/models/student.py app/api/journal.py
git commit -m "feat: Redis session cache for student state (5 min TTL)"
```

---

## Task 7: ARQ Task Queue Setup

**Files:**
- Modify: `adeline-brain/requirements.txt`
- Create: `adeline-brain/app/worker.py`
- Create: `adeline-brain/app/jobs/__init__.py`
- Create: `adeline-brain/app/jobs/lesson_jobs.py`

- [ ] **Step 1: Add arq to requirements.txt**

Append to `adeline-brain/requirements.txt`:

```
arq==0.26.1
```

- [ ] **Step 2: Create the lesson job**

Create `adeline-brain/app/jobs/__init__.py` (empty).

Create `adeline-brain/app/jobs/lesson_jobs.py`:

```python
"""
ARQ job: lesson generation off the HTTP request path.

Accepts a serialized LessonRequest + student_id.
Runs the full orchestrator (embed → canonical check → agent → registrar).
Stores result in Redis via ARQ's native result system (TTL: 1 hour).
"""
import logging
from app.schemas.api_models import LessonRequest

logger = logging.getLogger(__name__)


async def generate_lesson_job(ctx: dict, lesson_request_dict: dict, student_id: str) -> dict:
    """
    ARQ job function. ctx is provided by ARQ worker (contains shared connections).
    Returns a dict (JSON-serializable LessonResponse).
    """
    from app.agents.orchestrator import run_orchestrator

    logger.info(
        f"[ARQ] generate_lesson_job start — "
        f"student={student_id[:8]} topic={lesson_request_dict.get('topic', '')[:40]}"
    )
    lesson_request = LessonRequest(**lesson_request_dict)
    response = await run_orchestrator(lesson_request, student_id)
    logger.info(f"[ARQ] generate_lesson_job complete — lesson_id={response.lesson_id}")
    return response.model_dump(mode="json")
```

- [ ] **Step 3: Create app/worker.py**

Create `adeline-brain/app/worker.py`:

```python
"""
ARQ WorkerSettings — runs as a separate Railway service.

Start command: arq app.worker.WorkerSettings

Shares the same Docker image as the web service.
Initializes the same DB connections the orchestrator requires.
"""
import logging
import os
from arq.connections import RedisSettings
from arq import cron

from app.jobs.lesson_jobs import generate_lesson_job

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def startup(ctx: dict) -> None:
    """Initialize connections needed by lesson generation jobs."""
    from app.connections.pgvector_client import hippocampus
    from app.connections.neo4j_client import neo4j_client

    try:
        await hippocampus.connect()
        logger.info("[ARQ Worker] Hippocampus connected")
    except Exception as e:
        logger.warning(f"[ARQ Worker] Hippocampus unavailable: {e}")

    try:
        await neo4j_client.connect()
        logger.info("[ARQ Worker] Neo4j connected")
    except Exception as e:
        logger.warning(f"[ARQ Worker] Neo4j unavailable (ZPD degraded): {e}")


async def shutdown(ctx: dict) -> None:
    """Clean up connections on worker shutdown."""
    from app.connections.pgvector_client import hippocampus
    from app.connections.neo4j_client import neo4j_client

    try:
        await hippocampus.disconnect()
    except Exception:
        pass
    try:
        await neo4j_client.close()
    except Exception:
        pass


class WorkerSettings:
    # ARQ requires actual function objects, not string paths
    functions = [generate_lesson_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(_REDIS_URL)
    max_jobs = 4
    job_timeout = 120          # seconds — matches Gunicorn timeout
    keep_result = 3600         # keep results in Redis for 1 hour
    keep_result_forever = False
    retry_jobs = False         # don't retry failed lessons — return error to user
```

- [ ] **Step 4: Verify worker imports cleanly**

```bash
cd adeline-brain
pip install arq==0.26.1
python -c "from app.worker import WorkerSettings; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt app/worker.py app/jobs/__init__.py app/jobs/lesson_jobs.py
git commit -m "feat: ARQ task queue for async lesson generation"
```

---

## Task 8: Async Lesson Endpoint — Enqueue + Status Route

**Files:**
- Modify: `adeline-brain/app/api/lessons.py`
- Create: `adeline-brain/tests/test_arq_lesson.py`

- [ ] **Step 1: Write the failing test**

Create `adeline-brain/tests/test_arq_lesson.py`:

```python
"""Tests for async lesson generation via ARQ."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_generate_lesson_returns_job_id(auth_headers):
    """POST /lesson/generate returns job_id immediately, not a full LessonResponse."""
    mock_job = MagicMock()
    mock_job.job_id = "test-job-id-123"

    with patch("app.api.lessons.get_current_user_id", return_value="student-123"), \
         patch("app.api.lessons._enqueue_lesson_job", new_callable=AsyncMock, return_value=mock_job):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/lesson/generate", json={
                "student_id": "student-123",
                "track": "TRUTH_HISTORY",
                "topic": "Frederick Douglass",
                "is_homestead": False,
                "grade_level": "5",
            }, headers=auth_headers)

    assert resp.status_code == 202
    body = resp.json()
    assert body["job_id"] == "test-job-id-123"
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_lesson_status_done(auth_headers):
    """GET /lesson/status/{job_id} returns done + result when ARQ job is complete."""
    from arq.jobs import JobStatus

    mock_job = MagicMock()
    mock_job.status = AsyncMock(return_value=JobStatus.complete)
    mock_job.result = AsyncMock(return_value={"lesson_id": "abc", "title": "Test Lesson"})

    with patch("app.api.lessons.get_current_user_id", return_value="student-123"), \
         patch("app.api.lessons._get_arq_job", return_value=mock_job):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/lesson/status/test-job-id-123", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["result"]["lesson_id"] == "abc"


@pytest.mark.asyncio
async def test_lesson_status_queued(auth_headers):
    """GET /lesson/status/{job_id} returns queued while job is waiting."""
    from arq.jobs import JobStatus

    mock_job = MagicMock()
    mock_job.status = AsyncMock(return_value=JobStatus.queued)

    with patch("app.api.lessons.get_current_user_id", return_value="student-123"), \
         patch("app.api.lessons._get_arq_job", return_value=mock_job):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/lesson/status/test-job-id-123", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_arq_lesson.py -v
```
Expected: FAIL — `_enqueue_lesson_job` and `_get_arq_job` not found

- [ ] **Step 3: Add imports and helpers to lessons.py**

At the top of `adeline-brain/app/api/lessons.py`, add these imports after the existing ones:

```python
import arq
from arq.connections import RedisSettings, create_pool as arq_create_pool
from arq.jobs import Job as ARQJob, JobStatus
```

Add these two helper functions after the existing `_embed` function:

```python
async def _get_arq_redis_pool():
    """Create a short-lived ARQ Redis pool for enqueue/status operations."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return await arq_create_pool(RedisSettings.from_dsn(redis_url))


async def _enqueue_lesson_job(lesson_request_dict: dict, student_id: str):
    """Enqueue a lesson generation job and return the ARQ Job object."""
    pool = await _get_arq_redis_pool()
    job = await pool.enqueue_job(
        "generate_lesson_job",
        lesson_request_dict,
        student_id,
    )
    await pool.aclose()
    return job


def _get_arq_job(job_id: str, pool) -> ARQJob:
    """Return an ARQ Job handle for status checking."""
    return ARQJob(job_id, pool)
```

- [ ] **Step 4: Replace the generate_lesson endpoint**

In `adeline-brain/app/api/lessons.py`, find the `generate_lesson` function signature:

```python
@router.post(
    "/generate",
    response_model=LessonResponse,
)
@limiter.limit("20/hour")
async def generate_lesson(
    request: Request,
    lesson_request: LessonRequest,
    student_id: str = Depends(get_current_user_id),
):
```

Replace with:

```python
@router.post(
    "/generate",
    status_code=202,
)
@limiter.limit("20/hour")
async def generate_lesson(
    request: Request,
    lesson_request: LessonRequest,
    student_id: str = Depends(get_current_user_id),
):
    """
    Enqueue a lesson generation job and return immediately.

    Returns { job_id, status: "queued" } — poll GET /lesson/status/{job_id}
    for the result. Job completes in 5–45s depending on canonical cache state.
    """
    job = await _enqueue_lesson_job(lesson_request.model_dump(mode="json"), student_id)
    logger.info(
        f"[/lesson/generate] Enqueued job={job.job_id} "
        f"topic='{lesson_request.topic}' track={lesson_request.track.value}"
    )
    return {"job_id": job.job_id, "status": "queued"}
```

- [ ] **Step 5: Add the status endpoint to lessons.py**

Add this route after the generate endpoint:

```python
@router.get("/status/{job_id}")
async def get_lesson_status(
    job_id: str,
    student_id: str = Depends(get_current_user_id),
):
    """
    Poll for lesson generation status.

    Returns:
      { status: "queued" }               — job is waiting
      { status: "running" }              — job is executing
      { status: "done", result: {...} }  — lesson ready
      { status: "failed", error: "..." } — generation failed
    """
    pool = await _get_arq_redis_pool()
    job = _get_arq_job(job_id, pool)

    try:
        status = await job.status()

        if status == JobStatus.complete:
            result = await job.result(timeout=0)
            await pool.aclose()
            return {"status": "done", "result": result}

        elif status in (JobStatus.deferred, JobStatus.queued):
            await pool.aclose()
            return {"status": "queued"}

        elif status == JobStatus.in_progress:
            await pool.aclose()
            return {"status": "running"}

        elif status == JobStatus.not_found:
            await pool.aclose()
            return {"status": "not_found"}

        else:
            await pool.aclose()
            return {"status": "failed", "error": "Unknown job status"}

    except Exception as e:
        await pool.aclose()
        logger.error(f"[/lesson/status] Error checking job {job_id}: {e}")
        return {"status": "failed", "error": str(e)}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_arq_lesson.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add app/api/lessons.py tests/test_arq_lesson.py
git commit -m "feat: async lesson generation via ARQ (enqueue + status poll)"
```

---

## Task 9: Frontend Polling — brain-client.ts + AdelineChatPanel

**Files:**
- Modify: `adeline-ui/src/lib/brain-client.ts`
- Modify: `adeline-ui/src/components/AdelineChatPanel.tsx`

- [ ] **Step 1: Update brain-client.ts — generateLesson returns job_id**

In `adeline-ui/src/lib/brain-client.ts`, replace the `generateLesson` function:

```typescript
export interface LessonJobResponse {
  job_id: string;
  status: "queued";
}

export interface LessonStatusResponse {
  status: "queued" | "running" | "done" | "failed" | "not_found";
  result?: LessonResponse;
  error?: string;
}

export async function generateLesson(request: LessonRequest): Promise<LessonJobResponse> {
  const res = await fetch(`${BRAIN_URL}/lesson/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(request),
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`adeline-brain error: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<LessonJobResponse>;
}

export async function getLessonStatus(jobId: string): Promise<LessonStatusResponse> {
  const res = await fetch(`${BRAIN_URL}/lesson/status/${encodeURIComponent(jobId)}`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`lesson status error: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<LessonStatusResponse>;
}

/**
 * Poll /lesson/status/{jobId} until done or failed.
 * Calls onProgress with each status update.
 * Resolves with the final LessonResponse or rejects on timeout/failure.
 */
export async function pollLessonResult(
  jobId: string,
  options: {
    intervalMs?: number;
    timeoutMs?: number;
    onProgress?: (status: string) => void;
  } = {}
): Promise<LessonResponse> {
  const { intervalMs = 2000, timeoutMs = 90000, onProgress } = options;
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const statusResult = await getLessonStatus(jobId);
    onProgress?.(statusResult.status);

    if (statusResult.status === "done" && statusResult.result) {
      return statusResult.result;
    }

    if (statusResult.status === "failed") {
      throw new Error(statusResult.error ?? "Lesson generation failed");
    }

    if (statusResult.status === "not_found") {
      throw new Error("Lesson job not found — it may have expired");
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error("Lesson generation timed out after 90 seconds");
}
```

- [ ] **Step 2: Update AdelineChatPanel.tsx — replace single await with polling**

In `adeline-ui/src/components/AdelineChatPanel.tsx`, add `pollLessonResult` to the import:

```typescript
import { scaffold, generateLesson, pollLessonResult, listProjects, getProject, reportActivity } from "@/lib/brain-client";
```

Find the first `generateLesson` call site (around line 238, inside the chat submit handler). Replace the pattern:

```typescript
const lesson = await generateLesson({
```

with:

```typescript
const job = await generateLesson({
  student_id: studentId,
  track: activeLessonContext?.track ?? detectedTrack,
  topic: cleanedTopic,
  is_homestead: isHomestead,
  grade_level: gradeLevel,
});
const lesson = await pollLessonResult(job.job_id, {
  intervalMs: 2000,
  timeoutMs: 90000,
  onProgress: (status) => {
    if (status === "running") {
      // Update loading message — the component already shows a spinner
      logger.debug?.(`[Lesson] Generation status: ${status}`);
    }
  },
});
```

Find the second `generateLesson` call site (around line 276). Apply the same replacement pattern:

```typescript
const job = await generateLesson({
  student_id: studentId,
  track: activeLessonContext?.track ?? detectedTrack,
  topic: topicFromContext,
  is_homestead: isHomestead,
  grade_level: gradeLevel,
});
const lesson = await pollLessonResult(job.job_id, {
  intervalMs: 2000,
  timeoutMs: 90000,
});
```

Find the third `generateLesson` call site (around line 595, in the inner component). Apply the same replacement:

```typescript
const job = await generateLesson({
  student_id: studentId,
  track: selectedTrack,
  topic: topic,
  is_homestead: isHomestead,
  grade_level: gradeLevel,
});
const lesson: LessonResponse = await pollLessonResult(job.job_id, {
  intervalMs: 2000,
  timeoutMs: 90000,
});
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd adeline-ui
pnpm build 2>&1 | tail -20
```
Expected: build completes with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
cd ..
git add adeline-ui/src/lib/brain-client.ts adeline-ui/src/components/AdelineChatPanel.tsx
git commit -m "feat: frontend polling for async lesson generation"
```

---

## Task 10: Nightly Canonical Cache Warmup Job

**Files:**
- Create: `adeline-brain/app/jobs/warmup_jobs.py`
- Modify: `adeline-brain/app/worker.py`

- [ ] **Step 1: Create the warmup job**

Create `adeline-brain/app/jobs/warmup_jobs.py`:

```python
"""
Nightly canonical cache warmup job.

Queries all approved CanonicalLesson rows from Postgres and writes each to Redis.
Runs at 02:00 UTC via ARQ cron. Ensures Redis is never cold after restart.

This is the difference between a student's first lesson of the day taking
500ms (Redis hit) vs 3000ms (DB query + serialize).
"""
import json
import logging

from app.connections.canonical_store import canonical_store, REDIS_PREFIX
from app.connections.redis_client import redis_client

logger = logging.getLogger(__name__)


async def warmup_canonical_cache(ctx: dict) -> dict:
    """
    Load all approved canonical lessons from Postgres into Redis.
    Returns a summary dict for logging.
    """
    from app.config import get_db_conn

    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            'SELECT "topicSlug", topic, track, title, "blocksJson", "oasStandards", '
            '"researcherActivated", "agentName" '
            'FROM "CanonicalLesson" '
            'WHERE ("pendingApproval" IS FALSE OR "pendingApproval" IS NULL) '
            'ORDER BY "updatedAt" DESC',
        )
    finally:
        await conn.close()

    loaded = 0
    failed = 0

    for row in rows:
        slug = row["topicSlug"]
        record = {
            "id": None,
            "topic_slug": slug,
            "topic": row["topic"],
            "track": row["track"],
            "title": row["title"],
            "blocks": row["blocksJson"],
            "oas_standards": row["oasStandards"],
            "researcher_activated": row["researcherActivated"],
            "agent_name": row["agentName"],
            "pending_approval": False,
            "needs_review_reason": None,
        }
        try:
            await redis_client.set(
                f"{REDIS_PREFIX}{slug}",
                json.dumps(record),
                ex=None,  # no TTL — nightly job refreshes
            )
            loaded += 1
        except Exception as e:
            logger.warning(f"[Warmup] Failed to cache slug={slug}: {e}")
            failed += 1

    logger.info(f"[Warmup] Canonical cache warmed: {loaded} loaded, {failed} failed")
    return {"loaded": loaded, "failed": failed, "total": len(rows)}
```

- [ ] **Step 2: Register the cron job in worker.py**

In `adeline-brain/app/worker.py`, add the warmup import and update `WorkerSettings`.

Add after the existing `from app.jobs.lesson_jobs import generate_lesson_job` line:

```python
from app.jobs.warmup_jobs import warmup_canonical_cache
```

Update the `WorkerSettings` class to add `warmup_canonical_cache` and `cron_jobs`:

```python
class WorkerSettings:
    functions = [generate_lesson_job, warmup_canonical_cache]
    cron_jobs = [
        cron(warmup_canonical_cache, hour=2, minute=0),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(_REDIS_URL)
    max_jobs = 4
    job_timeout = 120
    keep_result = 3600
    keep_result_forever = False
    retry_jobs = False
```

- [ ] **Step 3: Verify worker imports cleanly**

```bash
cd adeline-brain
python -c "from app.worker import WorkerSettings; print(WorkerSettings.cron_jobs)"
```
Expected: prints the cron job list.

- [ ] **Step 4: Commit**

```bash
git add app/jobs/warmup_jobs.py app/worker.py
git commit -m "feat: nightly ARQ cron job to warm canonical lesson Redis cache"
```

---

## Task 11: GitHub Actions CI/CD

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-brain:
    name: Lint (adeline-brain)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install ruff
        run: pip install ruff==0.4.4
      - name: Lint
        run: ruff check adeline-brain/app/ adeline-brain/tests/

  test-brain:
    name: Tests (adeline-brain)
    runs-on: ubuntu-latest
    needs: lint-brain
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: adeline
          POSTGRES_PASSWORD: testpassword
          POSTGRES_DB: adeline_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      POSTGRES_DSN: postgresql://adeline:testpassword@localhost:5432/adeline_test
      REDIS_URL: redis://localhost:6379/0
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      SUPABASE_JWT_SECRET: test-secret-for-ci
      ADELINE_MODEL: claude-haiku-4-5-20251001
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          cd adeline-brain
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-httpx
      - name: Run Prisma migrations
        run: |
          cd adeline-brain
          DATABASE_URL=$POSTGRES_DSN prisma migrate deploy
      - name: Run tests
        run: |
          cd adeline-brain
          pytest tests/ -x --tb=short -q \
            --ignore=tests/test_genesis_fetch.py \
            --ignore=tests/test_sefaria_fetch.py \
            --ignore=tests/test_e2e_production_ready.py

  lint-ui:
    name: Lint (adeline-ui)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - uses: pnpm/action-setup@v3
        with:
          version: 9
      - name: Install dependencies
        run: cd adeline-ui && pnpm install --frozen-lockfile
      - name: Type check
        run: cd adeline-ui && pnpm exec tsc --noEmit

  deploy:
    name: Deploy to Railway
    runs-on: ubuntu-latest
    needs: [test-brain, lint-ui]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      - name: Install Railway CLI
        run: npm install -g @railway/cli
      - name: Deploy adeline-brain
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --service adeline-brain --detach
      - name: Deploy adeline-worker
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --service adeline-worker --detach
      - name: Deploy adeline-ui
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --service adeline-ui --detach
```

- [ ] **Step 2: Add required GitHub secrets**

In GitHub repo → Settings → Secrets and variables → Actions, add:
- `RAILWAY_TOKEN` — get from Railway dashboard → Account → Tokens
- `OPENAI_API_KEY` — your OpenAI key (for CI embedding tests)
- `ANTHROPIC_API_KEY` — your Anthropic key (for CI lesson tests)

If you don't want to use real API keys in CI, add this to the test run step:
```yaml
        run: |
          cd adeline-brain
          pytest tests/ -x --tb=short -q \
            --ignore=tests/test_genesis_fetch.py \
            --ignore=tests/test_sefaria_fetch.py \
            --ignore=tests/test_e2e_production_ready.py \
            --ignore=tests/test_e2e_declassified_lesson.py \
            -m "not slow"
```

- [ ] **Step 3: Add ruff to requirements.txt**

Append to `adeline-brain/requirements.txt`:

```
# CI / dev tools
ruff==0.4.4
pytest==8.2.0
pytest-asyncio==0.23.7
pytest-httpx==0.30.0
```

- [ ] **Step 4: Commit and push**

```bash
git add .github/workflows/ci.yml requirements.txt
git commit -m "feat: GitHub Actions CI/CD — lint + test + Railway deploy gate"
git push origin main
```

Expected: GitHub Actions starts running. Check Actions tab in GitHub.

- [ ] **Step 5: Verify pipeline passes**

Go to `https://github.com/<your-repo>/actions` and confirm all jobs go green. If any test fails, fix it before proceeding.

---

## Task 12: Git Pre-Commit Hook

**Files:**
- Create: `.git/hooks/pre-commit`

- [ ] **Step 1: Create the pre-commit hook**

Run this command (creates the hook file):

```bash
cat > .git/hooks/pre-commit << 'HOOK'
#!/bin/sh
# Block commits containing raw secrets.
# Patterns: OpenAI keys, Google API keys, Postgres connection strings.

PATTERNS="sk-proj-|sk-[A-Za-z0-9]{48}|AIza[0-9A-Za-z\-_]{35}|postgresql://[^:]+:[^@]+@"

if git diff --cached --name-only | xargs grep -rEl "$PATTERNS" 2>/dev/null | grep -v ".git/hooks/pre-commit"; then
    echo ""
    echo "ERROR: Potential secret found in staged files."
    echo "Remove secrets before committing. Use Railway env vars for production secrets."
    echo ""
    exit 1
fi
exit 0
HOOK
chmod +x .git/hooks/pre-commit
```

- [ ] **Step 2: Verify the hook blocks a bad commit**

```bash
echo 'OPENAI_API_KEY=sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx' > /tmp/test-secret.txt
git add /tmp/test-secret.txt 2>/dev/null || true
echo 'sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx' > test-secret-check.txt
git add test-secret-check.txt
git commit -m "test secret"
```
Expected: commit is BLOCKED with `ERROR: Potential secret found in staged files.`

```bash
# Clean up
git restore --staged test-secret-check.txt
rm test-secret-check.txt
```

- [ ] **Step 3: Commit (the hook itself doesn't go in the repo — it's in .git/)**

```bash
echo "Pre-commit hook installed — lives in .git/hooks/pre-commit (not committed)"
```
Note: `.git/hooks/` is not tracked by git. Each developer installs this locally. Document it in CLAUDE.md.

---

## Post-Deploy Checklist

After all tasks are committed and deployed to Railway:

- [ ] Railway shows 4 Gunicorn workers starting in logs
- [ ] `GET https://dearadeline.co/brain/health` returns `{ "redis": "ok", "status": "alive", ... }`
- [ ] `POST /lesson/generate` returns `{ "job_id": "...", "status": "queued" }` in < 500ms
- [ ] `GET /lesson/status/{job_id}` transitions from `queued` → `running` → `done`
- [ ] Sentry dashboard shows no unhandled exceptions on first lessons
- [ ] GitHub Actions shows green on the first push after Task 11
- [ ] ARQ worker service shows `[ARQ Worker] Hippocampus connected` in Railway logs

## Railway Service Configuration

After deploying, configure the `adeline-worker` service in Railway:
- **Start command:** `arq app.worker.WorkerSettings`
- **Same Docker image** as `adeline-brain`
- **Same env vars** as `adeline-brain` (share the service or copy vars)
- **No port binding needed** — the worker doesn't serve HTTP
