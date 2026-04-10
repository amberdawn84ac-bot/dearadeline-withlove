# Auth Hardening + Accessibility Pass

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this spec task-by-task.

**Goal:** Close API authentication gaps so every student-facing endpoint verifies JWT ownership, and fix the highest-priority accessibility issues across the UI.

**Architecture:** Two independent workstreams. Part 1 modifies `adeline-brain` API routes to enforce JWT-based ownership on all student data endpoints. Part 2 modifies `adeline-ui` components to meet WCAG 2.1 AA for keyboard navigation, screen readers, and color contrast.

---

## Part 1: API Auth Hardening

### Problem

The middleware (`app/api/middleware.py`) provides two solid auth dependencies:
- `get_current_user_id` — extracts `sub` (user UUID) from Supabase JWT
- `require_role(*roles)` — verifies JWT and checks role

However, many routes either (a) use no auth at all, or (b) use role checks but take `student_id` from the request body/URL instead of the JWT. This means any authenticated user can access or modify any other student's data.

### Route Audit

**Already secure (JWT-derived student_id):**
- `reading_session.py` — all 3 endpoints use `get_current_user_id`, ownership check on PATCH
- `admin_tasks.py` — ADMIN role + `get_current_user_id`
- `books.py` — role check + `get_current_user_id`
- `parent.py` — uses `get_current_user_id` for parent, queries children via `parentId`
- `onboarding.py` — uses `get_current_user_id`

**Role check but student_id from request body (IDOR vulnerable):**
- `journal.py` — `seal_journal` takes `body.student_id`; `get_progress` and `get_recent` take URL `student_id`
- `activities.py` — role check but `student_id` from body/URL
- `scaffold.py` — role check but `student_id` from body
- `lessons.py` — role check but `student_id` from body
- `transcripts.py` — role check but `student_id` from URL
- `projects.py` — role check but `student_id` from body

**No auth at all:**
- `learning_records.py` — all 5 endpoints: xAPI, transcript, reviews
- `students.py` — all 3 endpoints: register, profile, state
- `credits.py` — all 5 endpoints
- `learning_plan.py` — GET endpoint
- `subscriptions.py` — all 3 endpoints
- `experiments.py` — all 3 endpoints
- `bookshelf.py` — all 4 endpoints (public catalog, acceptable)
- `daily_bread.py` — GET (public, acceptable)

### Design

#### 1. Add `get_current_user_id` to all student-scoped routes

Every route that reads or writes student-specific data will use `student_id: str = Depends(get_current_user_id)` instead of accepting `student_id` from the request body or URL.

For routes that currently accept `student_id` in the request body (like `journal.py`'s `SealRequest`), the body field will be removed and replaced with the JWT-derived value.

For routes that take `student_id` as a URL path parameter (like `GET /journal/progress/{student_id}`), the parameter stays in the URL for REST semantics, but we add JWT verification and an ownership check: the JWT `sub` must match the URL `student_id`, or the caller must be a PARENT whose `parentId` matches, or ADMIN.

#### 2. New middleware helper: `get_current_user_id_or_parent`

For endpoints where a parent needs to view their child's data:

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
    - user is ADMIN
    - user is PARENT and student's parentId matches user_id
    """
```

This will be used on GET endpoints that take `student_id` in the URL path.

#### 3. Internal-only endpoints

`POST /learning/record` and `POST /learning/transcript` are called by the lesson generation pipeline (server-to-server), not by the browser. These will be protected with an internal API key check (`X-Internal-Key` header matching an env var) rather than JWT, since no user JWT is available in the server-to-server flow.

#### 4. Public endpoints (no auth needed)

These are intentionally public and will remain unprotected:
- `GET /bookshelf` — public book catalog
- `GET /bookshelf/{id}` — public book detail
- `GET /bookshelf/{id}/download` — public book download
- `GET /daily-bread` — daily verse (no student data)
- `GET /health`, `GET /health/truth` — health checks
- `GET /tracks` — track list
- `GET /experiments` — experiment catalog (read-only)

`POST /bookshelf/add` will be restricted to ADMIN role.

### Files to Modify

| File | Change |
|------|--------|
| `middleware.py` | Add `verify_student_access()` helper |
| `journal.py` | Replace `body.student_id` with JWT; add ownership check on GET endpoints |
| `learning_records.py` | Add JWT auth to GET endpoints; add internal key check to POST endpoints |
| `students.py` | Add JWT auth to all endpoints; register uses JWT `sub` as student ID |
| `credits.py` | Add JWT auth to all endpoints |
| `learning_plan.py` | Add JWT auth |
| `subscriptions.py` | Add JWT auth |
| `activities.py` | Replace body `student_id` with JWT |
| `scaffold.py` | Replace body `student_id` with JWT |
| `lessons.py` | Replace body `student_id` with JWT |
| `transcripts.py` | Add ownership check on GET endpoints |
| `projects.py` | Replace body `student_id` with JWT |
| `bookshelf.py` | Add ADMIN role check to `POST /add` |
| `config.py` | Add `INTERNAL_API_KEY` env var |

---

## Part 2: Accessibility Fixes

### Issues Found (by priority)

**Critical (blocks keyboard-only users):**

1. **`BookCard.tsx`** — `<article onClick>` without keyboard support. Needs `tabIndex={0}`, `role="button"`, `onKeyDown` handler for Enter/Space.

**High (screen reader gaps):**

2. **`AppSidebar.tsx`** — Mobile toggle button has no `aria-label`. Add `aria-label="Open menu"` / `"Close menu"`.

3. **`WelcomeFlow.tsx`** — Progress bar is a bare `<div>` with dynamic width. Add `role="progressbar"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax`.

4. **`CreditDashboard.tsx`** — Loading state is a plain `<div>`. Add `role="status"` and `aria-live="polite"`.

5. **`SpacedRepWidget.tsx`** — Rating buttons lack context. Add `aria-label` like `"Rate recall: Easy"`.

**Medium (color contrast):**

6. **Global pattern: `text-[#2F4731]/40` and `text-[#2F4731]/60`** — Both fail WCAG AA 4.5:1 contrast ratio on white/cream backgrounds.
   - `/40` on `#FFFEF7` = ~2.1:1 (fails)
   - `/60` on `#FFFEF7` = ~2.9:1 (fails)
   - Fix: bump to `/70` minimum for body text, `/50` for large text (18px+ or 14px bold)

### Files to Modify

| File | Change |
|------|--------|
| `BookCard.tsx` | Add keyboard support to clickable article |
| `AppSidebar.tsx` | Add `aria-label` to mobile toggle |
| `WelcomeFlow.tsx` | Add progressbar ARIA |
| `CreditDashboard.tsx` | Add `role="status"` to loading state |
| `SpacedRepWidget.tsx` | Add `aria-label` to rating buttons |
| Multiple components | Replace `/40` opacity with `/70`, `/60` with `/70` for small text |

### Not In Scope

- Full WCAG audit of every component (do incrementally)
- Skip tracing and focus management (complex, low ROI for MVP)
- `EPUBReader.tsx` — already has good ARIA coverage, skip

---

## Testing Strategy

**Auth:**
- For each modified route, verify: (a) request without JWT returns 401, (b) request with valid JWT for wrong student returns 403, (c) request with valid JWT for correct student succeeds, (d) ADMIN JWT can access any student
- Internal endpoints: verify `X-Internal-Key` works and missing key returns 401

**A11y:**
- Keyboard-only navigation through BookCard grid (Tab to focus, Enter to activate)
- Screen reader announcement of sidebar toggle, progress bars, loading states
- Contrast check with browser devtools on updated opacity values
