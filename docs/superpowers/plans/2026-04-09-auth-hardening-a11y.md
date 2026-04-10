# Auth Hardening + Accessibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all API authentication gaps so every student-facing endpoint verifies JWT ownership, and fix the highest-priority accessibility issues in the UI.

**Architecture:** Add `verify_student_access()` middleware helper for ownership checks on URL-param routes. Convert all body-sourced `student_id` fields to JWT-derived values. Protect internal server-to-server endpoints with `X-Internal-Key`. Fix keyboard navigation, screen reader, and contrast issues in 5 UI components.

**Tech Stack:** FastAPI + PyJWT (existing), asyncpg (existing), React + Tailwind (existing), Lucide icons (existing)

---

## File Structure

**Backend (adeline-brain/app/):**

| File | Responsibility | Change Type |
|------|---------------|-------------|
| `api/middleware.py` | Auth dependencies | Modify — add `verify_student_access()` and `require_internal_key()` |
| `config.py` | Env vars | Modify — add `INTERNAL_API_KEY` |
| `api/journal.py` | Journal seal/progress | Modify — JWT auth + ownership |
| `api/learning_records.py` | xAPI/transcript/SM-2 | Modify — internal key on writes, JWT on reads |
| `api/students.py` | Student CRUD | Modify — JWT auth |
| `api/credits.py` | Credit dashboard | Modify — JWT auth |
| `api/learning_plan.py` | Learning plan | Modify — JWT auth |
| `api/subscriptions.py` | Subscriptions | Modify — JWT auth |
| `api/activities.py` | Activity reports | Modify — JWT-derived student_id |
| `api/scaffold.py` | ZPD scaffold | Modify — JWT-derived student_id |
| `api/lessons.py` | Lesson generation | Modify — JWT-derived student_id |
| `api/transcripts.py` | Transcript views | Modify — JWT ownership check |
| `api/projects.py` | Project catalog | Modify — JWT-derived student_id |
| `api/bookshelf.py` | Book catalog | Modify — ADMIN on POST /add |

**Frontend (adeline-ui/src/components/):**

| File | Responsibility | Change Type |
|------|---------------|-------------|
| `reading-nook/BookCard.tsx` | Book card | Modify — keyboard support |
| `nav/AppSidebar.tsx` | Sidebar nav | Modify — aria-label on toggle |
| `onboarding/WelcomeFlow.tsx` | Onboarding flow | Modify — progressbar ARIA |
| `dashboard/CreditDashboard.tsx` | Credit view | Modify — loading state ARIA |
| `dashboard/SpacedRepWidget.tsx` | SM-2 review | Modify — button aria-labels |

---

### Task 1: Add `verify_student_access()` and `require_internal_key()` to middleware

**Files:**
- Modify: `adeline-brain/app/api/middleware.py:110-163`
- Modify: `adeline-brain/app/config.py:91`

- [ ] **Step 1: Add `INTERNAL_API_KEY` to config.py**

Add this line after `SUPABASE_JWT_SECRET` (line 91):

```python
# ── Internal API Key (server-to-server calls from lesson pipeline) ──────────
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key-not-for-production")
```

- [ ] **Step 2: Add `verify_student_access()` to middleware.py**

Add the following after the existing `get_current_user_id` function (after line 163):

```python
async def verify_student_access(
    student_id: str,
    authorization: Optional[str] = Header(default=None),
) -> str:
    """
    Verify the caller can access this student's data.
    Returns the authenticated user_id.

    Allowed if:
    - user_id == student_id (student accessing own data)
    - user role is ADMIN
    - user role is PARENT and student's parentId matches user_id
    """
    token = _extract_bearer_token(authorization)
    payload = _decode_jwt(token)
    user_id = _extract_user_id(payload)
    role_str = _extract_role(payload)

    # Student accessing own data
    if user_id == student_id:
        return user_id

    # Admin can access any student
    if role_str == UserRole.ADMIN.value:
        return user_id

    # Parent can access their children
    if role_str == UserRole.PARENT.value:
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                'SELECT id FROM "User" WHERE id = $1 AND "parentId" = $2',
                student_id, user_id,
            )
        finally:
            await conn.close()
        if row:
            return user_id

    raise HTTPException(
        status_code=403,
        detail="You do not have access to this student's data.",
    )
```

- [ ] **Step 3: Add `require_internal_key()` to middleware.py**

Add after `verify_student_access`:

```python
def require_internal_key(
    x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key"),
) -> str:
    """
    Verify the request carries a valid internal API key.
    Used for server-to-server calls (lesson pipeline → learning records).
    """
    from app.config import INTERNAL_API_KEY
    if not x_internal_key or x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing internal API key.",
        )
    return x_internal_key
```

- [ ] **Step 4: Commit**

```bash
git add adeline-brain/app/api/middleware.py adeline-brain/app/config.py
git commit -m "feat: add verify_student_access() and require_internal_key() auth helpers"
```

---

### Task 2: Harden `journal.py` — JWT ownership on all endpoints

**Files:**
- Modify: `adeline-brain/app/api/journal.py`

The `seal_journal` endpoint currently takes `student_id` from `body.student_id`. The GET endpoints take it from the URL path but only check role, not ownership.

- [ ] **Step 1: Add `get_current_user_id` import**

Replace the middleware import at line 14:

```python
from app.api.middleware import require_role
```

with:

```python
from app.api.middleware import require_role, get_current_user_id, verify_student_access
```

- [ ] **Step 2: Modify `seal_journal` to use JWT student_id**

Replace the route function signature and first lines (lines 57-72):

```python
@router.post("/seal", response_model=SealResponse)
async def seal_journal(
    body: SealRequest,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Seal a lesson into the student's journal.

    - Upserts (student_id, lesson_id) into student_journal
    - Returns updated track_progress so the UI can refresh the dashboard
    """
    logger.info(
        f"[/journal/seal] student={body.student_id} "
        f"lesson={body.lesson_id} track={body.track.value} "
        f"blocks={body.completed_blocks}"
    )
```

with:

```python
@router.post("/seal", response_model=SealResponse)
async def seal_journal(
    body: SealRequest,
    student_id: str = Depends(get_current_user_id),
):
    """
    Seal a lesson into the student's journal.

    - Upserts (student_id, lesson_id) into student_journal
    - Returns updated track_progress so the UI can refresh the dashboard
    """
    logger.info(
        f"[/journal/seal] student={student_id} "
        f"lesson={body.lesson_id} track={body.track.value} "
        f"blocks={body.completed_blocks}"
    )
```

- [ ] **Step 3: Update `seal_journal` body to use JWT student_id**

Replace all `body.student_id` references in the function with `student_id`:

In the `journal_store.seal()` call (line 74):

```python
        track_progress = await journal_store.seal(
            student_id=student_id,
```

In the `_record_mastery_safe` call (line 88):

```python
        asyncio.create_task(
            _record_mastery_safe(student_id, body.track.value, body.oas_standards)
        )
```

- [ ] **Step 4: Remove `student_id` from `SealRequest` model**

Change the `SealRequest` class (lines 24-30) — remove `student_id` field:

```python
class SealRequest(BaseModel):
    lesson_id:        str
    track:            Track
    completed_blocks: int = Field(default=0, ge=0)
    oas_standards:    list[dict[str, Any]] = Field(default_factory=list)
    evidence_sources: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 5: Add ownership check to GET endpoints**

Replace `get_progress` (lines 107-119):

```python
@router.get("/progress/{student_id}", response_model=ProgressResponse)
async def get_progress(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
):
    """Return all track progress counts for a student."""
    try:
        track_progress = await journal_store.get_track_progress(student_id)
    except Exception as e:
        logger.exception("[/journal/progress] DB error")
        raise HTTPException(status_code=500, detail=str(e))

    return ProgressResponse(student_id=student_id, track_progress=track_progress)
```

Replace `get_recent` (lines 122-138):

```python
@router.get("/recent/{student_id}", response_model=RecentResponse)
async def get_recent(
    student_id: str,
    limit: int = 10,
    _user_id: str = Depends(verify_student_access),
):
    """Return the most recently sealed lessons for a student."""
    try:
        entries = await journal_store.get_recent(student_id, limit=min(limit, 50))
    except Exception as e:
        logger.exception("[/journal/recent] DB error")
        raise HTTPException(status_code=500, detail=str(e))

    return RecentResponse(
        student_id=student_id,
        entries=[RecentEntry(**e) for e in entries],
    )
```

Note: `verify_student_access` takes `student_id` as its first param and reads `authorization` from the header — FastAPI will inject both the path param and the header automatically.

- [ ] **Step 6: Commit**

```bash
git add adeline-brain/app/api/journal.py
git commit -m "fix(auth): journal endpoints use JWT student_id, add ownership checks on GETs"
```

---

### Task 3: Harden `learning_records.py` — internal key on writes, JWT on reads

**Files:**
- Modify: `adeline-brain/app/api/learning_records.py`

POST `/learning/record` and `/learning/transcript` are called server-to-server by the lesson pipeline. GET endpoints and POST `/learning/reviews` are called by the browser.

- [ ] **Step 1: Add auth imports**

Add at the top of the file, after the existing imports (around line 23):

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from app.api.middleware import get_current_user_id, verify_student_access, require_internal_key
```

(Replace the existing `from fastapi import APIRouter, Depends, HTTPException, Query` line.)

- [ ] **Step 2: Protect POST `/learning/record` with internal key**

Change the route decorator and signature (line 131-132):

```python
@router.post("/record", response_model=RecordLearningResponse)
async def record_learning(
    payload: RecordLearningRequest,
    _key: str = Depends(require_internal_key),
):
```

- [ ] **Step 3: Protect POST `/learning/transcript` with internal key**

Change the route decorator and signature (line 181-182):

```python
@router.post("/transcript", response_model=SealTranscriptResponse)
async def seal_transcript(
    entry: TranscriptEntryIn,
    _key: str = Depends(require_internal_key),
):
```

- [ ] **Step 4: Add ownership check to GET `/learning/transcript/{student_id}`**

Change the route signature (line 238-239):

```python
@router.get("/transcript/{student_id}")
async def get_transcript(
    student_id: str,
    limit: int = Query(50, le=200),
    _user_id: str = Depends(verify_student_access),
):
```

- [ ] **Step 5: Add ownership check to GET `/learning/reviews/{student_id}`**

Change the route signature (line 268-269):

```python
@router.get("/reviews/{student_id}", response_model=DueReviewsResponse)
async def get_due_reviews(
    student_id: str,
    limit: int = Query(20, le=50),
    _user_id: str = Depends(verify_student_access),
):
```

- [ ] **Step 6: Add JWT auth to POST `/learning/reviews`**

The SM-2 review submit currently takes `student_id` from the request body. Change to use JWT:

Change the route signature (line 310-311):

```python
@router.post("/reviews", response_model=SM2ReviewResponse)
async def submit_review(
    payload: SM2ReviewSubmit,
    student_id: str = Depends(get_current_user_id),
):
```

Then replace all `payload.student_id` with `student_id` in the function body (lines 329, 363):

Line 329:
```python
            WHERE "studentId" = $1 AND "conceptId" = $2
            """,
            student_id, payload.concept_id,
```

Line 363:
```python
            str(uuid.uuid4()), student_id, payload.concept_id,
```

Line 370-371:
```python
        f"[SM2] Review submitted: student={student_id}, "
```

Remove `student_id` from `SM2ReviewSubmit` model (line 87):

```python
class SM2ReviewSubmit(BaseModel):
    concept_id: str
    quality:    int          # 0-5 per SM-2 spec
    track:      str = "TRUTH_HISTORY"  # track the concept belongs to
```

- [ ] **Step 7: Update lesson pipeline to send internal key**

The lesson pipeline calls `/learning/record` and `/learning/transcript`. Find where these calls are made and add the `X-Internal-Key` header.

Search for calls to these endpoints in `adeline-brain/app/api/lessons.py`. The function `_persist_learning_records` (around line 60) calls `record_learning` and `seal_transcript` directly as Python functions, not via HTTP. Since these are direct function calls within the same process, the `Depends()` injection won't apply when called directly.

**Important realization:** These POST endpoints are called as direct Python function calls from within `lessons.py`, not via HTTP requests. The `Depends()` mechanism only works for HTTP requests routed through FastAPI. For the internal call path, we need to make the dependency optional — allow either internal key OR direct Python invocation.

Update the protection to check: if the request comes via HTTP (has headers), require the key. If it's a direct call, allow it. The simplest approach: make the internal key dependency check optional when no authorization header is present at all (meaning it's a direct call, not an HTTP request).

Actually, looking at `lessons.py` more carefully — it calls the underlying DB functions directly, not the route functions. So the route protection is correct: HTTP callers need the key, and internal code calls the DB layer directly. No changes needed to `lessons.py`.

- [ ] **Step 8: Commit**

```bash
git add adeline-brain/app/api/learning_records.py
git commit -m "fix(auth): learning_records endpoints protected with internal key and JWT ownership"
```

---

### Task 4: Harden `students.py` — JWT auth on all endpoints

**Files:**
- Modify: `adeline-brain/app/api/students.py`

- [ ] **Step 1: Add auth imports**

Replace the imports at the top (lines 15-17):

```python
import asyncpg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
```

with:

```python
import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.api.middleware import get_current_user_id, verify_student_access
```

- [ ] **Step 2: Protect POST `/students/register` with JWT**

The register endpoint should use the JWT `sub` as the student ID (the Supabase auth user ID IS the student ID). Change the route (lines 88-133):

```python
@router.post("/register", response_model=StudentProfile, status_code=200)
async def register_student(
    body: RegisterRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Create or update a student profile.
    Uses the authenticated user's ID as the student ID.
    """
    conn = await _get_conn()
    try:
        await conn.execute(_INIT_SQL)
        row = await conn.fetchrow(
            """
            INSERT INTO student_profiles (id, name, email, grade_level, is_homestead)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE SET
                name         = EXCLUDED.name,
                email        = COALESCE(EXCLUDED.email, student_profiles.email),
                grade_level  = EXCLUDED.grade_level,
                is_homestead = EXCLUDED.is_homestead,
                updated_at   = now()
            RETURNING id, name, email, grade_level, is_homestead,
                      created_at::text, updated_at::text
            """,
            user_id, body.name, body.email, body.grade_level, body.is_homestead,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Email already registered")
    except Exception as e:
        logger.exception("[/students/register] DB error")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

    return StudentProfile(
        student_id=row["id"],
        name=row["name"],
        email=row["email"],
        grade_level=row["grade_level"],
        is_homestead=row["is_homestead"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
```

Remove `student_id` from `RegisterRequest` model (lines 57-66):

```python
class RegisterRequest(BaseModel):
    name:         str = Field(default="", max_length=200)
    email:        str | None = Field(default=None)
    grade_level:  str = Field(default="K", pattern=r"^(K|[1-9]|1[0-2])$")
    is_homestead: bool = Field(default=False)
```

- [ ] **Step 3: Protect GET endpoints with ownership check**

Replace `get_profile` (lines 136-167):

```python
@router.get("/{student_id}", response_model=StudentProfile)
async def get_profile(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
):
    """Fetch a student's profile by ID."""
    conn = await _get_conn()
    try:
        await conn.execute(_INIT_SQL)
        row = await conn.fetchrow(
            """
            SELECT id, name, email, grade_level, is_homestead,
                   created_at::text, updated_at::text
            FROM student_profiles WHERE id = $1
            """,
            student_id,
        )
    except Exception as e:
        logger.exception("[/students/{id}] DB error")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Student not found")

    return StudentProfile(
        student_id=row["id"],
        name=row["name"],
        email=row["email"],
        grade_level=row["grade_level"],
        is_homestead=row["is_homestead"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
```

Replace `get_student_state` (lines 170-212):

```python
@router.get("/{student_id}/state", response_model=StudentStateResponse)
async def get_student_state(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
):
    """
    Return the full StudentState (mastery scores, bands, lesson counts per track).
    Used by ZPDRecommendations in the UI.
    """
    conn = await _get_conn()
    try:
        await conn.execute(_INIT_SQL)
        row = await conn.fetchrow(
            "SELECT grade_level, is_homestead FROM student_profiles WHERE id = $1",
            student_id,
        )
    except Exception:
        row = None
    finally:
        await conn.close()

    grade_level  = row["grade_level"]  if row else "K"
    is_homestead = row["is_homestead"] if row else False

    try:
        student_state = await load_student_state(student_id)
    except Exception as e:
        logger.warning(f"[/students/{student_id}/state] load_student_state failed: {e}")
        student_state = None

    tracks_out: dict = {}
    if student_state:
        for track_name, mastery in student_state.tracks.items():
            tracks_out[track_name] = {
                "mastery_score": mastery.mastery_score,
                "mastery_band":  mastery.mastery_band.value,
                "lesson_count":  mastery.lesson_count,
            }

    return StudentStateResponse(
        student_id=student_id,
        grade_level=grade_level,
        is_homestead=is_homestead,
        tracks=tracks_out,
    )
```

- [ ] **Step 4: Update module docstring**

Replace the module docstring (lines 1-10):

```python
"""
Students API — /students/*

Student profile CRUD with Supabase JWT authentication.

POST /students/register    — Upsert a student profile (uses JWT sub as student ID)
GET  /students/{student_id}          — Fetch profile (ownership verified)
GET  /students/{student_id}/state    — Full StudentState (ownership verified)
"""
```

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/app/api/students.py
git commit -m "fix(auth): students endpoints require JWT auth with ownership verification"
```

---

### Task 5: Harden remaining routes — credits, learning_plan, subscriptions, activities, scaffold, lessons, transcripts, projects, bookshelf

**Files:**
- Modify: `adeline-brain/app/api/credits.py`
- Modify: `adeline-brain/app/api/learning_plan.py`
- Modify: `adeline-brain/app/api/subscriptions.py`
- Modify: `adeline-brain/app/api/activities.py`
- Modify: `adeline-brain/app/api/scaffold.py`
- Modify: `adeline-brain/app/api/lessons.py`
- Modify: `adeline-brain/app/api/transcripts.py`
- Modify: `adeline-brain/app/api/projects.py`
- Modify: `adeline-brain/app/api/bookshelf.py`

Each file follows the same pattern: add auth imports and wire up dependencies. The changes are mechanical.

- [ ] **Step 1: `credits.py` — add JWT auth**

Add import at top:

```python
from fastapi import APIRouter, Depends, HTTPException
from app.api.middleware import verify_student_access, get_current_user_id
from app.schemas.api_models import UserRole
from app.api.middleware import require_role
```

`GET /credits/available-profiles` stays public (no student data).

Add ownership check to student-specific endpoints:

```python
@router.get("/credits/{student_id}/profile")
async def get_student_profile(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
) -> dict:
```

```python
@router.put("/credits/{student_id}/profile")
async def set_student_profile(
    student_id: str,
    profile_key: str,
    _user_id: str = Depends(verify_student_access),
) -> dict:
```

```python
@router.get("/credits/{student_id}")
async def get_credit_dashboard(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
) -> CreditDashboardResponse:
```

```python
@router.post("/credits/{student_id}/approve/{proposal_id}")
async def approve_course_proposal(
    student_id: str,
    proposal_id: str,
    _user_id: str = Depends(verify_student_access),
) -> dict:
```

- [ ] **Step 2: `learning_plan.py` — add JWT auth**

Add import and ownership check:

```python
from app.api.middleware import verify_student_access
```

```python
@router.get("/{student_id}", response_model=LearningPlanResponse)
async def get_learning_plan(
    student_id: str,
    # ... existing params ...
    _user_id: str = Depends(verify_student_access),
):
```

- [ ] **Step 3: `subscriptions.py` — add JWT auth**

Add import:

```python
from fastapi import Depends
from app.api.middleware import get_current_user_id, verify_student_access
```

For `POST /upsert` and `POST /cancel`: add `_user_id: str = Depends(get_current_user_id)`.
For `GET /{user_id}`: add `_auth_user: str = Depends(verify_student_access)` (treating `user_id` path param like `student_id`).

- [ ] **Step 4: `activities.py` — replace body student_id with JWT**

The `report_activity` endpoint already has `require_role` but takes `body.student_id`. Add `get_current_user_id`:

```python
from app.api.middleware import require_role, get_current_user_id, verify_student_access
```

Change `report_activity`:

```python
@router.post("/report", response_model=ActivityReportResponse)
async def report_activity(
    body: ActivityReportRequest,
    student_id: str = Depends(get_current_user_id),
):
```

Replace all `body.student_id` in the function with `student_id`.

Change `list_activities`:

```python
@router.get("/{student_id}", response_model=ActivityListResponse)
async def list_activities(
    student_id: str,
    limit: int = Query(50, le=200),
    _user_id: str = Depends(verify_student_access),
):
```

- [ ] **Step 5: `scaffold.py` — replace body student_id with JWT**

Add import:

```python
from app.api.middleware import require_role, get_current_user_id, verify_student_access
```

Change `scaffold_response`:

```python
@router.post(
    "/scaffold",
    response_model=ScaffoldResponseBody,
)
async def scaffold_response(
    body: ScaffoldRequest,
    student_id: str = Depends(get_current_user_id),
):
```

Replace `body.student_id` with `student_id` in the function body.

Change `get_student_state`:

```python
@router.get(
    "/student-state/{student_id}",
)
async def get_student_state(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
):
```

- [ ] **Step 6: `lessons.py` — replace body student_id with JWT**

Add import:

```python
from app.api.middleware import require_role, get_current_user_id
```

Change `generate_lesson`:

```python
@router.post(
    "/generate",
    response_model=LessonResponse,
)
async def generate_lesson(
    request: LessonRequest,
    student_id: str = Depends(get_current_user_id),
):
```

Replace `request.student_id` with `student_id` throughout the function.

- [ ] **Step 7: `transcripts.py` — add ownership check**

Add import:

```python
from app.api.middleware import require_role, verify_student_access
```

Add `_user_id: str = Depends(verify_student_access)` to both GET endpoints that take `student_id` in the URL path. Remove the `require_role` dependency from the decorator (ownership check subsumes it).

- [ ] **Step 8: `projects.py` — replace body student_id with JWT**

Add import:

```python
from app.api.middleware import require_role, get_current_user_id
```

For `POST /{project_id}/start` and `POST /{project_id}/seal`, add `student_id: str = Depends(get_current_user_id)` and replace body-sourced `student_id`.

- [ ] **Step 9: `bookshelf.py` — ADMIN on POST /add**

Add import:

```python
from fastapi import Depends
from app.api.middleware import require_role
from app.schemas.api_models import UserRole
```

Change `add_book`:

```python
@router.post(
    "/add",
    response_model=AddBookResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def add_book(request: AddBookRequest, background_tasks: BackgroundTasks):
```

- [ ] **Step 10: Commit all remaining route changes**

```bash
git add adeline-brain/app/api/credits.py adeline-brain/app/api/learning_plan.py adeline-brain/app/api/subscriptions.py adeline-brain/app/api/activities.py adeline-brain/app/api/scaffold.py adeline-brain/app/api/lessons.py adeline-brain/app/api/transcripts.py adeline-brain/app/api/projects.py adeline-brain/app/api/bookshelf.py
git commit -m "fix(auth): harden all remaining routes with JWT auth and ownership checks"
```

---

### Task 6: Update UI auth headers

**Files:**
- Modify: `adeline-ui/src/lib/brain-client.ts`

The UI's `brain-client.ts` already sends the Supabase JWT in requests. Verify this, and ensure the `sealJournal` function no longer sends `student_id` in the body (since the server now gets it from JWT).

- [ ] **Step 1: Check brain-client.ts auth header pattern**

Read `adeline-ui/src/lib/brain-client.ts` and verify all fetch calls include the Authorization header with the Supabase session token.

- [ ] **Step 2: Update `sealJournal` to omit `student_id` from body**

The `sealJournal` function sends a body with `student_id`. Since the server now gets this from the JWT, remove `student_id` from the request body. The server still needs `lesson_id`, `track`, `completed_blocks`, `oas_standards`, and `evidence_sources`.

Find the `sealJournal` function and remove the `student_id` field from the body it sends. Also update the TypeScript interface if there is one.

- [ ] **Step 3: Verify other client functions**

Check that functions calling `/learning/reviews` (SM-2 submit), `/activities/report`, `/lesson/scaffold`, and `/lesson/generate` match the updated server expectations (no `student_id` in body where JWT is now used).

- [ ] **Step 4: Commit**

```bash
git add adeline-ui/src/lib/brain-client.ts
git commit -m "fix(auth): update brain-client to match new JWT-based auth contract"
```

---

### Task 7: Accessibility — BookCard keyboard support

**Files:**
- Modify: `adeline-ui/src/components/reading-nook/BookCard.tsx:146-157`

- [ ] **Step 1: Add keyboard handler and ARIA to article**

Replace the `<article>` opening tag (around line 147):

```tsx
    <article
      onClick={handleClick}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      className={`
        w-[180px] rounded-lg overflow-hidden
        transition-all duration-200 cursor-pointer
        ${hovering ? "shadow-lg border border-amber-200" : "shadow-sm border border-[#E7DAC3]"}
        bg-white
      `}
    >
```

with:

```tsx
    <article
      onClick={handleClick}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onStart?.(book.id); } }}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onFocus={() => setHovering(true)}
      onBlur={() => setHovering(false)}
      tabIndex={0}
      role="button"
      aria-label={`Open ${book.title} by ${book.author}`}
      className={`
        w-[180px] rounded-lg overflow-hidden
        transition-all duration-200 cursor-pointer
        ${hovering ? "shadow-lg border border-amber-200" : "shadow-sm border border-[#E7DAC3]"}
        bg-white focus:outline-none focus:ring-2 focus:ring-[#BD6809] focus:ring-offset-2
      `}
    >
```

- [ ] **Step 2: Commit**

```bash
git add adeline-ui/src/components/reading-nook/BookCard.tsx
git commit -m "fix(a11y): BookCard keyboard navigation and screen reader support"
```

---

### Task 8: Accessibility — AppSidebar toggle, WelcomeFlow progress, CreditDashboard loading, SpacedRepWidget buttons

**Files:**
- Modify: `adeline-ui/src/components/nav/AppSidebar.tsx:38`
- Modify: `adeline-ui/src/components/onboarding/WelcomeFlow.tsx:99-104`
- Modify: `adeline-ui/src/components/dashboard/CreditDashboard.tsx:51`
- Modify: `adeline-ui/src/components/dashboard/SpacedRepWidget.tsx:248-253`

- [ ] **Step 1: AppSidebar — add aria-label to toggle button**

Replace line 38:

```tsx
        <button onClick={() => setIsOpen(!isOpen)} className="p-2 text-[#2F4731]">
```

with:

```tsx
        <button onClick={() => setIsOpen(!isOpen)} className="p-2 text-[#2F4731]" aria-label={isOpen ? "Close menu" : "Open menu"}>
```

- [ ] **Step 2: WelcomeFlow — add progressbar ARIA**

Replace the progress bar (lines 99-104):

```tsx
          {/* Progress bar */}
          <div className="mt-4 h-1 bg-white/20 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#BD6809] transition-all duration-300"
              style={{ width: `${((step + 1) / 4) * 100}%` }}
            />
          </div>
```

with:

```tsx
          {/* Progress bar */}
          <div className="mt-4 h-1 bg-white/20 rounded-full overflow-hidden" role="progressbar" aria-valuenow={step + 1} aria-valuemin={0} aria-valuemax={4} aria-label={`Setup progress: step ${step + 1} of 4`}>
            <div
              className="h-full bg-[#BD6809] transition-all duration-300"
              style={{ width: `${((step + 1) / 4) * 100}%` }}
            />
          </div>
```

- [ ] **Step 3: CreditDashboard — add status role to loading state**

Replace line 51:

```tsx
  if (isLoading) return <div className="p-6 text-center">Loading credit data...</div>;
```

with:

```tsx
  if (isLoading) return <div className="p-6 text-center" role="status" aria-live="polite">Loading credit data...</div>;
```

- [ ] **Step 4: SpacedRepWidget — add aria-labels to rating buttons**

Replace the button in the QUALITY_LABELS map (around lines 249-253):

```tsx
              <button
                key={value}
                onClick={() => submitRating(value)}
                className="rounded-lg py-1.5 text-[11px] font-bold transition-opacity hover:opacity-80"
                style={styles}
```

with:

```tsx
              <button
                key={value}
                onClick={() => submitRating(value)}
                aria-label={`Rate recall: ${label}`}
                className="rounded-lg py-1.5 text-[11px] font-bold transition-opacity hover:opacity-80"
                style={styles}
```

- [ ] **Step 5: Commit**

```bash
git add adeline-ui/src/components/nav/AppSidebar.tsx adeline-ui/src/components/onboarding/WelcomeFlow.tsx adeline-ui/src/components/dashboard/CreditDashboard.tsx adeline-ui/src/components/dashboard/SpacedRepWidget.tsx
git commit -m "fix(a11y): add ARIA labels, progressbar roles, and live regions"
```

---

### Task 9: Accessibility — Color contrast fixes

**Files:**
- Multiple components across `adeline-ui/src/components/`

The pattern `text-[#2F4731]/40` (opacity 40%) and `text-[#2F4731]/60` (opacity 60%) on cream/white backgrounds fails WCAG AA contrast requirements. The fix: bump `/40` to `/70` and `/60` to `/70` for small text.

- [ ] **Step 1: Find all instances of low-contrast text**

Search for `text-[#2F4731]/40` and `text-[#2F4731]/60` across all UI components. These are the primary offenders.

For `/40` instances: change to `/60` (used for decorative/supplementary text that's meant to be de-emphasized — going to `/70` would make it too prominent).

For `/60` instances on text smaller than 18px: change to `/70`.

Exception: keep `/40` and `/60` on elements where the text is purely decorative or redundant (like a label that duplicates adjacent information).

- [ ] **Step 2: Apply contrast fixes**

Use find-and-replace across the component files. The main files to check:

- `BookCard.tsx` — `text-[#2F4731]/60` on author name
- `AppSidebar.tsx` — `text-[#2F4731]/60` on nav labels
- `SpacedRepWidget.tsx` — `text-[#2F4731]/50` on labels
- `WelcomeFlow.tsx` — various opacity levels
- `dashboard/` components — overview cards and labels

Replace `text-[#2F4731]/40` with `text-[#2F4731]/60` where the text carries meaning.
Replace `text-[#2F4731]/50` with `text-[#2F4731]/70` for small body text.
Replace `text-[#2F4731]/60` with `text-[#2F4731]/70` for text below 14px bold or 18px regular.

Note: only change instances where the text is meaningful content (descriptions, labels, metadata). Leave decorative separators and borders as-is.

- [ ] **Step 3: Commit**

```bash
git add adeline-ui/src/components/
git commit -m "fix(a11y): improve color contrast ratios to meet WCAG AA"
```
