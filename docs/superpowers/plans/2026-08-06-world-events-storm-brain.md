# World Events — The Storm — Brain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the adeline-brain backend for The Storm — a globally-scheduled, per-town-evaluated World Event with prep tracking and a treasury consequence.

**Architecture:** Two new columns on the existing `Town` table (`stormPrepCount`, `lastStormCycleEvaluated`), and two new routes appended directly to the existing `app/api/towns.py` (not a new file — these are genuinely part of the Town resource and that file already has the router/auth/connection infrastructure this needs). The storm calendar itself is computed, not stored — no new table, no scheduled job.

**Tech Stack:** Python, FastAPI, asyncpg — same stack and conventions as the existing Town system.

## Global Constraints

- Every endpoint path must match the spec exactly: `docs/superpowers/specs/2026-08-06-world-events-storm-design.md` (Adelinemobile repo) Section "API (adeline-brain)".
- New routes are added to the EXISTING `app/api/towns.py` file (which already has `router = APIRouter(prefix="/towns", ...)`, registered unprefixed in `main.py`) — do not create a new router file, do not touch `main.py` (nothing new to register).
- Auth: both new routes use the existing `_require_town_member(conn, user_id, town_id)` helper already defined in `towns.py` — same pattern as `get_town`/`patch_treasury`/`get_supply`/`patch_supply`.
- DB errors beyond expected cases must be caught (`except asyncpg.PostgresError`), logged server-side, generic 500 — never leak `str(e)`. This codebase's established convention (learned the hard way twice already this session): any route with an explicit-status raise (like a member-check 403) INSIDE its `try` block needs `except HTTPException: raise` before the broader `except asyncpg.PostgresError` catch, so the specific status isn't swallowed.
- Treasury penalty floors at 0 via `GREATEST(..., 0)`, matching the existing pattern in `patch_supply`/`patch_treasury`.
- The schedule constants (`STORM_CYCLE_DAYS`, `STORM_WARNING_DAYS`, `STORM_ANCHOR`) are hardcoded module-level constants, not environment-configurable, per the spec's explicit v1 scope.

---

## File Structure

| File | Change |
|---|---|
| `prisma/migrations/20260806_add_storm_fields/migration.sql` | **New.** Adds `stormPrepCount`, `lastStormCycleEvaluated` to `Town`. |
| `prisma/schema.prisma` | Add the same 2 fields to `model Town`. |
| `app/api/towns.py` | Append storm phase computation + `GET /towns/{id}/storm` and `POST /towns/{id}/storm/prep`. |

---

### Task 1: Migration + Prisma schema

**Files:**
- Create: `prisma/migrations/20260806_add_storm_fields/migration.sql`
- Modify: `prisma/schema.prisma`

- [ ] **Step 1: Create the migration file**

```sql
-- World Events: The Storm. Town-level prep counter and idempotency marker
-- for the globally-scheduled, per-town-evaluated storm event. See
-- docs/superpowers/specs/2026-08-06-world-events-storm-design.md
-- (Adelinemobile repo) for the full design.
ALTER TABLE "Town" ADD COLUMN IF NOT EXISTS "stormPrepCount" INTEGER NOT NULL DEFAULT 0;
ALTER TABLE "Town" ADD COLUMN IF NOT EXISTS "lastStormCycleEvaluated" INTEGER NOT NULL DEFAULT -1;
```

- [ ] **Step 2: Apply it against the database**

Connect with `psql "$POSTGRES_DSN"` (or `$DATABASE_URL`) and run the SQL above. Expected: both `ALTER TABLE` statements succeed with no errors.

- [ ] **Step 3: Add the equivalent fields to `model Town` in `prisma/schema.prisma`**

Find `model Town { ... }` (added in the prior Town & Player Systems plan) and add:
```prisma
  stormPrepCount          Int      @default(0)
  lastStormCycleEvaluated Int      @default(-1)
```

- [ ] **Step 4: Commit**

```bash
git add prisma/migrations/20260806_add_storm_fields prisma/schema.prisma
git commit -m "feat: add storm prep tracking fields to Town"
```

---

### Task 2: Storm phase computation + endpoints

**Files:**
- Modify: `app/api/towns.py`

**Interfaces:**
- Consumes: `_require_town_member`, `_get_conn`, `router`, `logger` — all already defined earlier in this same file.
- Produces: `GET /towns/{town_id}/storm`, `POST /towns/{town_id}/storm/prep` — consumed by the sibling Adelinemobile plan.

- [ ] **Step 1: Add the schedule constants and phase-computation helper**

Add near the top of `app/api/towns.py`, after the existing `BUILDING_KEYS` constant (around line 29-34):

```python
from datetime import date, datetime, timezone

# World Events: The Storm. A fixed, globally-shared calendar — every Town is
# on the same cycle. See docs/superpowers/specs/2026-08-06-world-events-storm-design.md
# (Adelinemobile repo) for the full design and the "why" behind these numbers.
STORM_CYCLE_DAYS = 21
STORM_WARNING_DAYS = 4
STORM_ANCHOR = date(2026, 8, 1)
STORM_PREP_THRESHOLD = 10
STORM_TREASURY_PENALTY = 50


def _storm_phase(today: date) -> tuple[str, int, int]:
    """Returns (phase, cycle, days_until_hit) for the given date.

    phase is 'hit' on the exact storm day, 'warning' within STORM_WARNING_DAYS
    of it, otherwise 'calm'. cycle is a 0-indexed count of how many storm
    cycles have elapsed since STORM_ANCHOR.
    """
    days_since_anchor = (today - STORM_ANCHOR).days
    cycle = days_since_anchor // STORM_CYCLE_DAYS
    day_in_cycle = days_since_anchor % STORM_CYCLE_DAYS
    days_until_hit = STORM_CYCLE_DAYS - day_in_cycle if day_in_cycle != 0 else 0

    if day_in_cycle == 0:
        phase = "hit"
    elif days_until_hit <= STORM_WARNING_DAYS:
        phase = "warning"
    else:
        phase = "calm"

    return phase, cycle, days_until_hit
```

- [ ] **Step 2: Add the request/response models**

Add near the other Pydantic models in this file (after `SupplyOut`, before the `_load_town` helper):

```python
class StormStatusOut(BaseModel):
    phase: str  # 'calm' | 'warning' | 'hit'
    cycle: int
    days_until_hit: int
    prep_count: int
    prep_threshold: int
    treasury: int


class StormPrepOut(BaseModel):
    prep_count: int
```

- [ ] **Step 3: Add the two routes**

Add at the end of the file, after `patch_supply`:

```python
@router.get("/{town_id}/storm", response_model=StormStatusOut)
async def get_storm_status(town_id: str, user_id: str = Depends(get_current_user_id)):
    today = datetime.now(timezone.utc).date()
    phase, cycle, days_until_hit = _storm_phase(today)

    conn = await _get_conn()
    try:
        await _require_town_member(conn, user_id, town_id)

        row = await conn.fetchrow(
            'SELECT "stormPrepCount", "lastStormCycleEvaluated", treasury FROM "Town" WHERE id = $1',
            town_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Town not found.")

        prep_count = row["stormPrepCount"]
        treasury = row["treasury"]
        last_evaluated = row["lastStormCycleEvaluated"]

        # A full cycle has passed since we last evaluated — settle it now,
        # regardless of current phase (covers nobody opening the app again
        # until well after the storm has passed).
        if cycle - 1 > last_evaluated:
            evaluated_cycle = cycle - 1
            if prep_count < STORM_PREP_THRESHOLD:
                treasury_row = await conn.fetchrow(
                    'UPDATE "Town" SET treasury = GREATEST(treasury - $1, 0), '
                    '"stormPrepCount" = 0, "lastStormCycleEvaluated" = $2 '
                    'WHERE id = $3 RETURNING treasury, "stormPrepCount"',
                    STORM_TREASURY_PENALTY, evaluated_cycle, town_id,
                )
            else:
                treasury_row = await conn.fetchrow(
                    'UPDATE "Town" SET "stormPrepCount" = 0, "lastStormCycleEvaluated" = $1 '
                    'WHERE id = $2 RETURNING treasury, "stormPrepCount"',
                    evaluated_cycle, town_id,
                )
            treasury = treasury_row["treasury"]
            prep_count = treasury_row["stormPrepCount"]
    except HTTPException:
        raise
    except asyncpg.PostgresError:
        logger.exception("Failed to load storm status")
        raise HTTPException(status_code=500, detail="Could not load storm status.")
    finally:
        await conn.close()

    return StormStatusOut(
        phase=phase, cycle=cycle, days_until_hit=days_until_hit,
        prep_count=prep_count, prep_threshold=STORM_PREP_THRESHOLD, treasury=treasury,
    )


@router.post("/{town_id}/storm/prep", response_model=StormPrepOut)
async def add_storm_prep(town_id: str, user_id: str = Depends(get_current_user_id)):
    conn = await _get_conn()
    try:
        await _require_town_member(conn, user_id, town_id)
        row = await conn.fetchrow(
            'UPDATE "Town" SET "stormPrepCount" = "stormPrepCount" + 1 WHERE id = $1 RETURNING "stormPrepCount"',
            town_id,
        )
    except HTTPException:
        raise
    except asyncpg.PostgresError:
        logger.exception("Failed to record storm prep")
        raise HTTPException(status_code=500, detail="Could not record storm prep.")
    finally:
        await conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Town not found.")
    return StormPrepOut(prep_count=row["stormPrepCount"])
```

- [ ] **Step 4: Verify the file imports cleanly**

Run: `python -c "import app.api.towns"` from the `adeline-brain` directory.
Expected: no `ImportError`/`SyntaxError`.

- [ ] **Step 5: Commit**

```bash
git add app/api/towns.py
git commit -m "feat: add storm phase computation, GET/POST storm status and prep endpoints"
```

---

### Task 3: End-to-end smoke test

**Files:** none (verification only)

The real storm calendar won't produce a `warning` or `hit` phase for weeks from `STORM_ANCHOR = 2026-08-01` under normal dates, so this task temporarily patches the constants to force an immediate warning window, verifies the full flow, then reverts.

- [ ] **Step 1: Start the server** (same env setup as prior tasks this session — `POSTGRES_DSN`/`DATABASE_URL` from `.env`, `SUPABASE_JWT_SECRET` exported)

```bash
uvicorn app.main:app --port 8001
```

- [ ] **Step 2: Register a student and create a town** (reuses existing endpoints)

```bash
RESP=$(curl -s -X POST http://localhost:8001/auth/student/register -H "Content-Type: application/json" \
  -d '{"display_name":"Storm Test","username":"stormtest1","pin":"1234"}')
echo "$RESP"
TOKEN=$(echo "$RESP" | python -c "import json,sys; print(json.load(sys.stdin)['token'])")

TOWN_RESP=$(curl -s -X POST http://localhost:8001/towns -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"Storm Town"}')
echo "$TOWN_RESP"
TOWN_ID=$(echo "$TOWN_RESP" | python -c "import json,sys; print(json.load(sys.stdin)['id'])")
```

- [ ] **Step 3: Check storm status against the real (far-future) calendar**

```bash
curl -s http://localhost:8001/towns/$TOWN_ID/storm -H "Authorization: Bearer $TOKEN"
```
Expected: 200, `"phase": "calm"` (since `STORM_ANCHOR` is 2026-08-01 and no cycle boundary has been crossed yet in the near term — the exact cycle/days_until_hit numbers depend on today's real date, that's fine, just confirm `"phase"` is a valid value and the response shape matches `StormStatusOut`).

- [ ] **Step 4: Temporarily force a warning-phase test**

Stop the server (Ctrl+C). Temporarily edit `app/api/towns.py`'s `STORM_ANCHOR` to a date 18 days in the future from today (`STORM_CYCLE_DAYS - STORM_WARNING_DAYS + 1` days out puts you inside the warning window) — e.g. if today is 2026-08-06, set `STORM_ANCHOR = date(2026, 8, 24)`. Restart the server:
```bash
uvicorn app.main:app --port 8001
```

- [ ] **Step 5: Confirm warning phase and test prep counting**

```bash
curl -s http://localhost:8001/towns/$TOWN_ID/storm -H "Authorization: Bearer $TOKEN"
```
Expected: `"phase": "warning"`, `"days_until_hit"` between 1 and 4, `"prep_count": 0`.

```bash
for i in 1 2 3; do
  curl -s -X POST http://localhost:8001/towns/$TOWN_ID/storm/prep -H "Authorization: Bearer $TOKEN"
  echo
done
```
Expected: three responses, `{"prep_count": 1}`, `{"prep_count": 2}`, `{"prep_count": 3}`.

- [ ] **Step 6: Force the cycle to have "passed" and confirm evaluation applies the penalty**

Stop the server. Edit `STORM_ANCHOR` again, this time to a date far enough in the past that a full cycle plus the warning window has already elapsed since the town's `lastStormCycleEvaluated` (-1) — e.g. `STORM_ANCHOR = date(2026, 6, 1)` (safely more than 21 days before today). Restart the server.

```bash
curl -s http://localhost:8001/towns/$TOWN_ID/storm -H "Authorization: Bearer $TOKEN"
```
Expected: 200. Since `prep_count` was only 3 (below `STORM_PREP_THRESHOLD = 10`), the response should show `"treasury"` reduced by 50 from whatever it was before (likely `0` since nothing else touched this town's treasury — confirm it's `GREATEST(0 - 50, 0) = 0`, i.e. floored, not negative), and `"prep_count": 0` (reset).

- [ ] **Step 7: Revert the temporary `STORM_ANCHOR` edit**

```bash
git diff app/api/towns.py
git checkout -- app/api/towns.py
```
Expected: `STORM_ANCHOR` back to `date(2026, 8, 1)` as committed in Task 2. Confirm with `git diff app/api/towns.py` showing no changes.

- [ ] **Step 8: Clean up test data**

Delete the test student and town from the database (same pattern as prior smoke tests this session — connect via the same `POSTGRES_DSN`, delete the `TownBuilding`/`User`/`Town` rows for `stormtest1`'s town).

- [ ] **Step 9: Stop the server, no commit for this task** (verification only — Task 2's commit already covers the real code)
