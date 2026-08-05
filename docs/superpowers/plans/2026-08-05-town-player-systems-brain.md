# Town & Player Systems — Brain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the adeline-brain backend for the Town & Player Systems spec — a joinable Town entity, a dual-layer (town-pooled + individual) resource model for money/property/inventory, and individual reputation/achievements.

**Architecture:** New Postgres tables (`Town`, `TownBuilding`, `Item`, `TownSupply`, `PlayerInventory`, `Achievement`, `PlayerAchievement`) plus a `townId`/`reputation` column added to the existing `User` table. Two new router files (`app/api/towns.py`, `app/api/player_systems.py`) reuse the existing bearer-token auth (`get_current_user_id`, `verify_student_access`) and raw-asyncpg query style established by `app/api/student_auth.py` and `app/api/students.py` earlier this session. Both routers register unprefixed in `app/main.py`, matching how Adelinemobile's `/api/brain/*` proxy forwards paths through unchanged.

**Tech Stack:** Python, FastAPI, asyncpg (raw SQL against Postgres — this codebase does not use the Prisma Python client for queries, only for schema documentation), slowapi (rate limiting).

## Global Constraints

- Every endpoint path must match the spec exactly: `docs/superpowers/specs/2026-08-05-town-player-systems-design.md` (in the Adelinemobile repo) Section "API (adeline-brain, FastAPI)".
- New routers register **unprefixed** in `app/main.py` (not `/brain`-prefixed) — matching the existing `students_router`/`student_auth_router` pattern, required because Adelinemobile's `server.ts` proxy forwards `/api/brain/*` as `BRAIN_URL + <path>` with no `/brain` segment.
- A kid belongs to zero or one Town — enforced via a nullable `townId` FK directly on `User`, not a join table.
- Money/property/inventory are dual-layer (town-pooled AND individual); skill trees/reputation/achievements are individual only, no town-level version — do not add a town-level reputation/achievement table.
- Migrations are hand-written SQL files under `prisma/migrations/<name>/migration.sql`, applied via `ALTER TABLE`/`CREATE TABLE ... IF NOT EXISTS` style, matching `prisma/migrations/20260804_add_student_mobile_fields/migration.sql`. Also update `prisma/schema.prisma` to stay truthful, per the same convention.
- Column names on `User`/new tables use the existing camelCase-quoted convention (e.g. `"townId"`, `"joinCode"`, `"itemId"`).
- All new authenticated endpoints must use `Depends(get_current_user_id)` or `Depends(verify_student_access)` as appropriate — never leave a data-mutating endpoint unauthenticated. Any endpoint keyed by a 6-character guessable code (join codes) must be rate-limited via the existing local-`Limiter` pattern (see `app/api/student_auth.py`'s `limiter = Limiter(key_func=get_remote_address)` + `@limiter.limit(...)` usage) — this codebase's earlier `/students/claim` endpoint shipped without this and needed a follow-up fix; do it right the first time here.
- DB errors beyond expected 404/409 cases must be caught (`except asyncpg.PostgresError`), logged server-side via `logger.exception(...)`, and returned as a generic 500 — never leak `str(e)` to the client. Multi-statement writes that must succeed together use `async with conn.transaction():`.

---

## File Structure

| File | Change |
|---|---|
| `prisma/migrations/20260805_add_town_player_systems/migration.sql` | **New.** All 7 new tables + `User.townId`/`User.reputation` columns. |
| `prisma/schema.prisma` | Add the new models + 2 new `User` fields. |
| `app/api/towns.py` | **New.** `POST /towns`, `POST /towns/join`, `GET /towns/{id}`, `PATCH /towns/{id}/treasury`, `GET/PATCH /towns/{id}/supply`. |
| `app/api/player_systems.py` | **New.** `GET/PATCH /students/{id}/inventory`, `PATCH /students/{id}/reputation`, `GET/POST /students/{id}/achievements`, `GET /items`, `GET /achievements`. |
| `app/main.py` | Register both new routers, unprefixed. |

---

### Task 1: Migration + Prisma schema

**Files:**
- Create: `prisma/migrations/20260805_add_town_player_systems/migration.sql`
- Modify: `prisma/schema.prisma`

- [ ] **Step 1: Create the migration file**

```sql
-- Town & Player Systems foundation: a joinable Town entity, dual-layer
-- (town-pooled + individual) resources for money/property/inventory, and
-- individual reputation/achievements. See
-- docs/superpowers/specs/2026-08-05-town-player-systems-design.md
-- (Adelinemobile repo) for the full design.

CREATE TABLE IF NOT EXISTS "Town" (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name        TEXT NOT NULL,
    "joinCode"  TEXT NOT NULL UNIQUE,
    treasury    INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "townId" TEXT REFERENCES "Town"(id);
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS reputation INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS "TownBuilding" (
    id            TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "townId"      TEXT NOT NULL REFERENCES "Town"(id) ON DELETE CASCADE,
    "buildingKey" TEXT NOT NULL,
    "createdAt"   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE ("townId", "buildingKey")
);

CREATE TABLE IF NOT EXISTS "Item" (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,
    description TEXT,
    "iconUrl"   TEXT,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "TownSupply" (
    id        TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "townId"  TEXT NOT NULL REFERENCES "Town"(id) ON DELETE CASCADE,
    "itemId"  TEXT NOT NULL REFERENCES "Item"(id),
    quantity  INTEGER NOT NULL DEFAULT 0,
    UNIQUE ("townId", "itemId")
);

CREATE TABLE IF NOT EXISTS "PlayerInventory" (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "studentId" TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    "itemId"    TEXT NOT NULL REFERENCES "Item"(id),
    quantity    INTEGER NOT NULL DEFAULT 0,
    UNIQUE ("studentId", "itemId")
);

CREATE TABLE IF NOT EXISTS "Achievement" (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    key         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT,
    icon        TEXT,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "PlayerAchievement" (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "studentId"     TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    "achievementId" TEXT NOT NULL REFERENCES "Achievement"(id),
    "earnedAt"      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE ("studentId", "achievementId")
);
```

- [ ] **Step 2: Apply it against the database**

Connect with `psql "$POSTGRES_DSN"` (or `$DATABASE_URL`) and run the SQL above. Expected: all `CREATE TABLE`/`ALTER TABLE` succeed with no errors.

- [ ] **Step 3: Add the equivalent models to `prisma/schema.prisma`**

Add two fields to the existing `model User { ... }` block (near `linkCode`):
```prisma
  townId               String?
  reputation           Int               @default(0)
```

Add these new models anywhere after `model User`:
```prisma
model Town {
  id        String   @id @default(uuid())
  name      String
  joinCode  String   @unique
  treasury  Int      @default(0)
  createdAt DateTime @default(now())
}

model TownBuilding {
  id           String   @id @default(uuid())
  townId       String
  buildingKey  String
  createdAt    DateTime @default(now())

  @@unique([townId, buildingKey])
}

model Item {
  id          String   @id @default(uuid())
  name        String
  type        String
  description String?
  iconUrl     String?
  createdAt   DateTime @default(now())
}

model TownSupply {
  id       String @id @default(uuid())
  townId   String
  itemId   String
  quantity Int    @default(0)

  @@unique([townId, itemId])
}

model PlayerInventory {
  id        String @id @default(uuid())
  studentId String
  itemId    String
  quantity  Int    @default(0)

  @@unique([studentId, itemId])
}

model Achievement {
  id          String   @id @default(uuid())
  key         String   @unique
  name        String
  description String?
  icon        String?
  createdAt   DateTime @default(now())
}

model PlayerAchievement {
  id            String   @id @default(uuid())
  studentId     String
  achievementId String
  earnedAt      DateTime @default(now())

  @@unique([studentId, achievementId])
}
```

- [ ] **Step 4: Commit**

```bash
git add prisma/migrations/20260805_add_town_player_systems prisma/schema.prisma
git commit -m "feat: add Town, Item, inventory, and achievement tables"
```

---

### Task 2: `app/api/towns.py` — create, join, view, treasury, supply

**Files:**
- Create: `app/api/towns.py`

**Interfaces:**
- Consumes: `get_current_user_id`, `verify_student_access` from `app.api.middleware`; `get_db_conn` from `app.config`.
- Produces: nothing consumed by other tasks in this plan (Task 3 is a separate, unrelated router).

- [ ] **Step 1: Create the file**

```python
"""
Towns — /towns/*

A Town is a joinable group (siblings, a co-op class, or solo play) that
kids belong to via a 6-character join code — independent of parent-child
linking. A kid belongs to zero or one Town (User.townId, nullable FK).

Money/property are dual-layer per the design spec: Town.treasury is the
shared pool; each kid's own wallet (User.adeCoins) is unaffected by this
file. TownSupply (this file) is the shared item pool; PlayerInventory
(app/api/player_systems.py) is the individual counterpart.
"""
import logging
import secrets

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.middleware import get_current_user_id
from app.config import get_db_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/towns", tags=["towns"])
limiter = Limiter(key_func=get_remote_address)


async def _get_conn():
    return await get_db_conn()


def _generate_join_code() -> str:
    return secrets.token_hex(3).upper()  # 6 hex chars, e.g. "A3F9C2"


# ── Models ────────────────────────────────────────────────────────────────────

class CreateTownRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class JoinTownRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class TreasuryDelta(BaseModel):
    delta: int


class SupplyDelta(BaseModel):
    item_id: str
    delta: int


class TownMember(BaseModel):
    id: str
    display_name: str
    username: str


class TownBuildingOut(BaseModel):
    building_key: str


class TownOut(BaseModel):
    id: str
    name: str
    join_code: str
    treasury: int
    members: list[TownMember] = []
    buildings: list[TownBuildingOut] = []


class TreasuryOut(BaseModel):
    treasury: int


class SupplyItemOut(BaseModel):
    item_id: str
    name: str
    type: str
    quantity: int


class SupplyOut(BaseModel):
    items: list[SupplyItemOut]


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _load_town(conn: asyncpg.Connection, town_id: str) -> TownOut | None:
    town_row = await conn.fetchrow('SELECT id, name, "joinCode", treasury FROM "Town" WHERE id = $1', town_id)
    if not town_row:
        return None
    member_rows = await conn.fetch(
        'SELECT id, name, username FROM "User" WHERE "townId" = $1', town_id,
    )
    building_rows = await conn.fetch(
        'SELECT "buildingKey" FROM "TownBuilding" WHERE "townId" = $1', town_id,
    )
    return TownOut(
        id=town_row["id"],
        name=town_row["name"],
        join_code=town_row["joinCode"],
        treasury=town_row["treasury"],
        members=[TownMember(id=r["id"], display_name=r["name"], username=r["username"] or "") for r in member_rows],
        buildings=[TownBuildingOut(building_key=r["buildingKey"]) for r in building_rows],
    )


async def _require_town_member(conn: asyncpg.Connection, user_id: str, town_id: str) -> None:
    row = await conn.fetchrow('SELECT "townId" FROM "User" WHERE id = $1', user_id)
    if not row or row["townId"] != town_id:
        raise HTTPException(status_code=403, detail="You are not a member of this town.")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=TownOut)
async def create_town(body: CreateTownRequest, user_id: str = Depends(get_current_user_id)):
    conn = await _get_conn()
    try:
        row = await conn.fetchrow('SELECT "townId" FROM "User" WHERE id = $1', user_id)
        if row and row["townId"]:
            raise HTTPException(status_code=409, detail="You are already in a town.")

        code = _generate_join_code()
        try:
            async with conn.transaction():
                town_row = await conn.fetchrow(
                    'INSERT INTO "Town" (name, "joinCode") VALUES ($1, $2) RETURNING id',
                    body.name, code,
                )
                await conn.execute('UPDATE "User" SET "townId" = $1 WHERE id = $2', town_row["id"], user_id)
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=500, detail="Could not generate a unique join code — please try again.")

        town = await _load_town(conn, town_row["id"])
    except asyncpg.PostgresError as e:
        logger.exception("Failed to create town")
        raise HTTPException(status_code=500, detail="Could not create town.")
    finally:
        await conn.close()

    if not town:
        raise HTTPException(status_code=500, detail="Could not create town.")
    return town


@router.post("/join", response_model=TownOut)
@limiter.limit("10/minute")
async def join_town(request: Request, body: JoinTownRequest, user_id: str = Depends(get_current_user_id)):
    code = body.code.strip().upper()
    conn = await _get_conn()
    try:
        row = await conn.fetchrow('SELECT "townId" FROM "User" WHERE id = $1', user_id)
        if row and row["townId"]:
            raise HTTPException(status_code=409, detail="You are already in a town.")

        town_row = await conn.fetchrow('SELECT id FROM "Town" WHERE "joinCode" = $1', code)
        if not town_row:
            raise HTTPException(status_code=404, detail="Join code not found.")

        await conn.execute('UPDATE "User" SET "townId" = $1 WHERE id = $2', town_row["id"], user_id)
        town = await _load_town(conn, town_row["id"])
    except asyncpg.PostgresError:
        logger.exception("Failed to join town")
        raise HTTPException(status_code=500, detail="Could not join town.")
    finally:
        await conn.close()

    if not town:
        raise HTTPException(status_code=500, detail="Could not join town.")
    return town


@router.get("/{town_id}", response_model=TownOut)
async def get_town(town_id: str, user_id: str = Depends(get_current_user_id)):
    conn = await _get_conn()
    try:
        await _require_town_member(conn, user_id, town_id)
        town = await _load_town(conn, town_id)
    finally:
        await conn.close()
    if not town:
        raise HTTPException(status_code=404, detail="Town not found.")
    return town


@router.patch("/{town_id}/treasury", response_model=TreasuryOut)
async def patch_treasury(town_id: str, body: TreasuryDelta, user_id: str = Depends(get_current_user_id)):
    conn = await _get_conn()
    try:
        await _require_town_member(conn, user_id, town_id)
        row = await conn.fetchrow(
            'UPDATE "Town" SET treasury = treasury + $1 WHERE id = $2 RETURNING treasury',
            body.delta, town_id,
        )
    except asyncpg.PostgresError:
        logger.exception("Failed to patch treasury")
        raise HTTPException(status_code=500, detail="Could not update treasury.")
    finally:
        await conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Town not found.")
    return TreasuryOut(treasury=row["treasury"])


@router.get("/{town_id}/supply", response_model=SupplyOut)
async def get_supply(town_id: str, user_id: str = Depends(get_current_user_id)):
    conn = await _get_conn()
    try:
        await _require_town_member(conn, user_id, town_id)
        rows = await conn.fetch(
            """
            SELECT i.id AS item_id, i.name, i.type, s.quantity
            FROM "TownSupply" s JOIN "Item" i ON i.id = s."itemId"
            WHERE s."townId" = $1
            """,
            town_id,
        )
    except asyncpg.PostgresError:
        logger.exception("Failed to load supply")
        raise HTTPException(status_code=500, detail="Could not load supply.")
    finally:
        await conn.close()
    return SupplyOut(items=[
        SupplyItemOut(item_id=r["item_id"], name=r["name"], type=r["type"], quantity=r["quantity"])
        for r in rows
    ])


@router.patch("/{town_id}/supply", response_model=SupplyItemOut)
async def patch_supply(town_id: str, body: SupplyDelta, user_id: str = Depends(get_current_user_id)):
    conn = await _get_conn()
    try:
        await _require_town_member(conn, user_id, town_id)
        item_row = await conn.fetchrow('SELECT id, name, type FROM "Item" WHERE id = $1', body.item_id)
        if not item_row:
            raise HTTPException(status_code=404, detail="Item not found.")

        row = await conn.fetchrow(
            """
            INSERT INTO "TownSupply" ("townId", "itemId", quantity)
            VALUES ($1, $2, GREATEST($3, 0))
            ON CONFLICT ("townId", "itemId") DO UPDATE
                SET quantity = GREATEST("TownSupply".quantity + $3, 0)
            RETURNING quantity
            """,
            town_id, body.item_id, body.delta,
        )
    except HTTPException:
        raise
    except asyncpg.PostgresError:
        logger.exception("Failed to patch supply")
        raise HTTPException(status_code=500, detail="Could not update supply.")
    finally:
        await conn.close()
    return SupplyItemOut(item_id=item_row["id"], name=item_row["name"], type=item_row["type"], quantity=row["quantity"])
```

- [ ] **Step 2: Verify the file imports cleanly**

Run: `python -c "import app.api.towns"` from the `adeline-brain` directory.
Expected: no `ImportError`/`SyntaxError`.

- [ ] **Step 3: Commit**

```bash
git add app/api/towns.py
git commit -m "feat: add Town create/join/view, treasury, and shared-supply endpoints"
```

---

### Task 3: `app/api/player_systems.py` — inventory, reputation, achievements, catalogs

**Files:**
- Create: `app/api/player_systems.py`

**Interfaces:**
- Consumes: `get_current_user_id`, `verify_student_access` from `app.api.middleware`; `get_db_conn` from `app.config`.
- Produces: nothing consumed by other tasks in this plan.

- [ ] **Step 1: Create the file**

```python
"""
Individual player systems — inventory, reputation, achievements — plus the
read-only Item/Achievement catalogs.

These are the individual counterpart to Town's shared treasury/supply
(app/api/towns.py). Per the design spec, skill trees/reputation/achievements
are individual-only — there is no town-level version of any of these.
"""
import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.middleware import verify_student_access
from app.config import get_db_conn

logger = logging.getLogger(__name__)
router = APIRouter(tags=["player-systems"])


async def _get_conn():
    return await get_db_conn()


# ── Models ────────────────────────────────────────────────────────────────────

class InventoryDelta(BaseModel):
    item_id: str
    delta: int


class InventoryItemOut(BaseModel):
    item_id: str
    name: str
    type: str
    quantity: int


class InventoryOut(BaseModel):
    items: list[InventoryItemOut]


class ReputationDelta(BaseModel):
    delta: int


class ReputationOut(BaseModel):
    reputation: int


class GrantAchievementRequest(BaseModel):
    achievement_key: str


class AchievementOut(BaseModel):
    key: str
    name: str
    description: str | None
    icon: str | None


class EarnedAchievementOut(AchievementOut):
    earned_at: str


class AchievementsOut(BaseModel):
    achievements: list[EarnedAchievementOut]


class ItemCatalogEntry(BaseModel):
    id: str
    name: str
    type: str
    description: str | None
    icon_url: str | None


class ItemCatalogOut(BaseModel):
    items: list[ItemCatalogEntry]


class AchievementCatalogOut(BaseModel):
    achievements: list[AchievementOut]


# ── Inventory ─────────────────────────────────────────────────────────────────

@router.get("/students/{student_id}/inventory", response_model=InventoryOut)
async def get_inventory(student_id: str, _user_id: str = Depends(verify_student_access)):
    conn = await _get_conn()
    try:
        rows = await conn.fetch(
            """
            SELECT i.id AS item_id, i.name, i.type, p.quantity
            FROM "PlayerInventory" p JOIN "Item" i ON i.id = p."itemId"
            WHERE p."studentId" = $1
            """,
            student_id,
        )
    except asyncpg.PostgresError:
        logger.exception("Failed to load inventory")
        raise HTTPException(status_code=500, detail="Could not load inventory.")
    finally:
        await conn.close()
    return InventoryOut(items=[
        InventoryItemOut(item_id=r["item_id"], name=r["name"], type=r["type"], quantity=r["quantity"])
        for r in rows
    ])


@router.patch("/students/{student_id}/inventory", response_model=InventoryItemOut)
async def patch_inventory(student_id: str, body: InventoryDelta, _user_id: str = Depends(verify_student_access)):
    conn = await _get_conn()
    try:
        item_row = await conn.fetchrow('SELECT id, name, type FROM "Item" WHERE id = $1', body.item_id)
        if not item_row:
            raise HTTPException(status_code=404, detail="Item not found.")

        row = await conn.fetchrow(
            """
            INSERT INTO "PlayerInventory" ("studentId", "itemId", quantity)
            VALUES ($1, $2, GREATEST($3, 0))
            ON CONFLICT ("studentId", "itemId") DO UPDATE
                SET quantity = GREATEST("PlayerInventory".quantity + $3, 0)
            RETURNING quantity
            """,
            student_id, body.item_id, body.delta,
        )
    except HTTPException:
        raise
    except asyncpg.PostgresError:
        logger.exception("Failed to patch inventory")
        raise HTTPException(status_code=500, detail="Could not update inventory.")
    finally:
        await conn.close()
    return InventoryItemOut(item_id=item_row["id"], name=item_row["name"], type=item_row["type"], quantity=row["quantity"])


# ── Reputation ────────────────────────────────────────────────────────────────

@router.patch("/students/{student_id}/reputation", response_model=ReputationOut)
async def patch_reputation(student_id: str, body: ReputationDelta, _user_id: str = Depends(verify_student_access)):
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            'UPDATE "User" SET reputation = reputation + $1 WHERE id = $2 RETURNING reputation',
            body.delta, student_id,
        )
    except asyncpg.PostgresError:
        logger.exception("Failed to patch reputation")
        raise HTTPException(status_code=500, detail="Could not update reputation.")
    finally:
        await conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found.")
    return ReputationOut(reputation=row["reputation"])


# ── Achievements ──────────────────────────────────────────────────────────────

@router.get("/students/{student_id}/achievements", response_model=AchievementsOut)
async def get_achievements(student_id: str, _user_id: str = Depends(verify_student_access)):
    conn = await _get_conn()
    try:
        rows = await conn.fetch(
            """
            SELECT a.key, a.name, a.description, a.icon, pa."earnedAt"
            FROM "PlayerAchievement" pa JOIN "Achievement" a ON a.id = pa."achievementId"
            WHERE pa."studentId" = $1
            ORDER BY pa."earnedAt" DESC
            """,
            student_id,
        )
    except asyncpg.PostgresError:
        logger.exception("Failed to load achievements")
        raise HTTPException(status_code=500, detail="Could not load achievements.")
    finally:
        await conn.close()
    return AchievementsOut(achievements=[
        EarnedAchievementOut(
            key=r["key"], name=r["name"], description=r["description"], icon=r["icon"],
            earned_at=r["earnedAt"].isoformat(),
        )
        for r in rows
    ])


@router.post("/students/{student_id}/achievements", response_model=EarnedAchievementOut)
async def grant_achievement(student_id: str, body: GrantAchievementRequest, _user_id: str = Depends(verify_student_access)):
    conn = await _get_conn()
    try:
        ach_row = await conn.fetchrow('SELECT id, key, name, description, icon FROM "Achievement" WHERE key = $1', body.achievement_key)
        if not ach_row:
            raise HTTPException(status_code=404, detail="Achievement not found.")

        row = await conn.fetchrow(
            """
            INSERT INTO "PlayerAchievement" ("studentId", "achievementId")
            VALUES ($1, $2)
            ON CONFLICT ("studentId", "achievementId") DO UPDATE SET "studentId" = EXCLUDED."studentId"
            RETURNING "earnedAt"
            """,
            student_id, ach_row["id"],
        )
    except HTTPException:
        raise
    except asyncpg.PostgresError:
        logger.exception("Failed to grant achievement")
        raise HTTPException(status_code=500, detail="Could not grant achievement.")
    finally:
        await conn.close()
    return EarnedAchievementOut(
        key=ach_row["key"], name=ach_row["name"], description=ach_row["description"], icon=ach_row["icon"],
        earned_at=row["earnedAt"].isoformat(),
    )


# ── Catalogs (read-only) ──────────────────────────────────────────────────────

@router.get("/items", response_model=ItemCatalogOut)
async def list_item_catalog():
    conn = await _get_conn()
    try:
        rows = await conn.fetch('SELECT id, name, type, description, "iconUrl" FROM "Item" ORDER BY name')
    except asyncpg.PostgresError:
        logger.exception("Failed to load item catalog")
        raise HTTPException(status_code=500, detail="Could not load item catalog.")
    finally:
        await conn.close()
    return ItemCatalogOut(items=[
        ItemCatalogEntry(id=r["id"], name=r["name"], type=r["type"], description=r["description"], icon_url=r["iconUrl"])
        for r in rows
    ])


@router.get("/achievements", response_model=AchievementCatalogOut)
async def list_achievement_catalog():
    conn = await _get_conn()
    try:
        rows = await conn.fetch('SELECT key, name, description, icon FROM "Achievement" ORDER BY name')
    except asyncpg.PostgresError:
        logger.exception("Failed to load achievement catalog")
        raise HTTPException(status_code=500, detail="Could not load achievement catalog.")
    finally:
        await conn.close()
    return AchievementCatalogOut(achievements=[
        AchievementOut(key=r["key"], name=r["name"], description=r["description"], icon=r["icon"])
        for r in rows
    ])
```

- [ ] **Step 2: Verify the file imports cleanly**

Run: `python -c "import app.api.player_systems"` from the `adeline-brain` directory.
Expected: no `ImportError`/`SyntaxError`.

- [ ] **Step 3: Commit**

```bash
git add app/api/player_systems.py
git commit -m "feat: add inventory, reputation, achievement, and catalog endpoints"
```

---

### Task 4: Add `town_id`/`reputation` to the student profile response

**Files:**
- Modify: `app/api/student_auth.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `StudentUserOut` (already consumed by Adelinemobile's `getStudentProfile`/register/login responses) now carries `town_id: str | None` and `reputation: int`.

The frontend needs to know a kid's `town_id` (to decide whether to show "create/join a town" vs "you're in Test Town") and `reputation` from the same profile call it already makes — without this task, Task 2's new Town columns on `User` are invisible to the client.

- [ ] **Step 1: Add the two fields to `StudentUserOut`**

In `app/api/student_auth.py`, find `class StudentUserOut(BaseModel):` and add two fields to it (after `link_code: str`):
```python
    town_id: str | None
    reputation: int
```

- [ ] **Step 2: Populate them in `load_student_user`**

Find the `load_student_user` function's SQL query (`SELECT u.id, u.name, u.username, ...`) and add `u."townId", u.reputation` to the selected columns. Find the `return StudentUserOut(...)` call at the end of that function and add:
```python
        town_id=row["townId"],
        reputation=row["reputation"],
```
(matching whatever argument style — keyword args — the existing call already uses).

- [ ] **Step 3: Verify the file imports cleanly**

Run: `python -c "import app.api.student_auth"` from the `adeline-brain` directory.
Expected: no `ImportError`/`SyntaxError`.

- [ ] **Step 4: Commit**

```bash
git add app/api/student_auth.py
git commit -m "feat: include town_id and reputation in student profile response"
```

---

### Task 5: Register both routers

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add imports** near the existing `from app.api.students import router as students_router` / `from app.api.student_auth import router as student_auth_router` lines

```python
from app.api.towns import router as towns_router
from app.api.player_systems import router as player_systems_router
```

- [ ] **Step 2: Register both, unprefixed**, directly after the existing `app.include_router(student_auth_router)` line (around line 239)

```python
app.include_router(towns_router)
app.include_router(player_systems_router)
```

- [ ] **Step 3: Verify the app starts**

Run: `uvicorn app.main:app --port 8001` from the `adeline-brain` directory (needs `POSTGRES_DSN`/`DATABASE_URL` and `SUPABASE_JWT_SECRET` set).
Expected: starts without error; `http://localhost:8001/docs` lists `POST /towns`, `POST /towns/join`, `GET /towns/{town_id}`, `PATCH /towns/{town_id}/treasury`, `GET/PATCH /towns/{town_id}/supply`, `GET/PATCH /students/{student_id}/inventory`, `PATCH /students/{student_id}/reputation`, `GET/POST /students/{student_id}/achievements`, `GET /items`, `GET /achievements`.

Kill the server with Ctrl+C.

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: register towns and player-systems routers"
```

---

### Task 6: Seed a minimal Item/Achievement catalog + end-to-end smoke test

**Files:**
- Create: `scripts/seed_town_player_systems.sql` (a few starter rows so the endpoints have something real to return in the smoke test and in early frontend development)

- [ ] **Step 1: Create a small seed file**

```sql
-- Minimal starter catalog for local/dev testing. Not exhaustive — more
-- items/achievements get added by the dev team directly as content grows
-- (no create-item API in v1, per the design spec).
INSERT INTO "Item" (name, type, description) VALUES
    ('Hammer', 'tool', 'For building and repairing.'),
    ('Plywood Sheet', 'material', 'Sturdy building material.'),
    ('Seed Packet', 'material', 'Plant something with this.')
ON CONFLICT DO NOTHING;

INSERT INTO "Achievement" (key, name, description, icon) VALUES
    ('first_town', 'Town Founder', 'Created or joined your first town.', '🏘️'),
    ('first_trade', 'First Trade', 'Contributed an item to the town supply.', '🤝')
ON CONFLICT (key) DO NOTHING;
```

- [ ] **Step 2: Apply it against the database**

Run this SQL against the same database Task 1's migration was applied to.

- [ ] **Step 3: Start the server** (same env as Task 5 Step 3)

```bash
uvicorn app.main:app --port 8001
```

- [ ] **Step 4: Register two test students and log in** (reuses the existing `/auth/student/register` and `/auth/student/login` endpoints)

```bash
curl -s -X POST http://localhost:8001/auth/student/register -H "Content-Type: application/json" \
  -d '{"display_name":"Town Test A","username":"towntesta","pin":"1234"}'
curl -s -X POST http://localhost:8001/auth/student/register -H "Content-Type: application/json" \
  -d '{"display_name":"Town Test B","username":"towntestb","pin":"1234"}'
```
Save each response's `token` and `student_id`.

- [ ] **Step 5: Confirm the profile endpoint shows `town_id: null` and `reputation: 0` before joining a town**

```bash
TOKEN_A="<paste>"
STUDENT_A_ID="<paste>"
curl -s http://localhost:8001/students/$STUDENT_A_ID/profile -H "Authorization: Bearer $TOKEN_A"
```
Expected: 200, response includes `"town_id": null, "reputation": 0` (Task 4's fields, confirmed wired end-to-end).

- [ ] **Step 6: Student A creates a town**

```bash
curl -s -X POST http://localhost:8001/towns -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
  -d '{"name":"Test Town"}'
```
Expected: 200 with `{"id": "...", "name": "Test Town", "join_code": "XXXXXX", "treasury": 0, "members": [{"id": "<A's id>", ...}], "buildings": []}`. Save `id` as `TOWN_ID` and `join_code` as `CODE`.

- [ ] **Step 7: Student B joins with the code**

```bash
TOKEN_B="<paste>"
curl -s -X POST http://localhost:8001/towns/join -H "Authorization: Bearer $TOKEN_B" -H "Content-Type: application/json" \
  -d "{\"code\":\"$CODE\"}"
```
Expected: 200, same town, now with 2 members.

- [ ] **Step 8: Student A adds to the shared treasury and supply**

```bash
curl -s -X PATCH http://localhost:8001/towns/$TOWN_ID/treasury -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" -d '{"delta": 100}'
# Expected: {"treasury": 100}

ITEM_ID="<paste an id from GET /items>"
curl -s http://localhost:8001/items
curl -s -X PATCH http://localhost:8001/towns/$TOWN_ID/supply -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
  -d "{\"item_id\":\"$ITEM_ID\",\"delta\":5}"
# Expected: {"item_id": "...", "name": "...", "type": "...", "quantity": 5}
```

- [ ] **Step 9: Student B (a fellow town member) can see the shared supply Student A added**

```bash
curl -s http://localhost:8001/towns/$TOWN_ID/supply -H "Authorization: Bearer $TOKEN_B"
```
Expected: 200, includes the item with quantity 5.

- [ ] **Step 10: A student who is NOT a member is rejected**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/towns/$TOWN_ID/supply -H "Authorization: Bearer <a third, non-member student's token, or omit for a 401>"
```
Expected: 403 (member check) or 401 (no token) — not 200.

- [ ] **Step 11: Individual inventory, reputation, and achievements work independently of the town**

```bash
curl -s -X PATCH http://localhost:8001/students/<A's id>/inventory -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" \
  -d "{\"item_id\":\"$ITEM_ID\",\"delta\":2}"
# Expected: {"item_id": "...", ..., "quantity": 2} — independent of the town's supply quantity from Step 7

curl -s -X PATCH http://localhost:8001/students/<A's id>/reputation -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" -d '{"delta": 10}'
# Expected: {"reputation": 10}

curl -s -X POST http://localhost:8001/students/<A's id>/achievements -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" -d '{"achievement_key":"first_town"}'
# Expected: 200 with the achievement + earned_at

curl -s -X POST http://localhost:8001/students/<A's id>/achievements -H "Authorization: Bearer $TOKEN_A" -H "Content-Type: application/json" -d '{"achievement_key":"first_town"}'
# Expected: 200 again (idempotent — granting twice is not an error)
```

- [ ] **Step 12: Stop the server, no commit for this task** (verification only — Step 1's seed file is the only artifact, already committable)

```bash
git add scripts/seed_town_player_systems.sql
git commit -m "chore: add minimal Item/Achievement seed data for town player systems"
```
