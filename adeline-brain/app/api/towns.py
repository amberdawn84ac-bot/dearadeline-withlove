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
from datetime import date, datetime, timezone

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

BUILDING_KEYS = [
    "adelines_kitchen", "the_library", "the_arena", "the_makers_lab",
    "the_creek_and_woods", "the_market", "the_chapel",
]

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


class StormStatusOut(BaseModel):
    phase: str  # 'calm' | 'warning' | 'hit'
    cycle: int
    days_until_hit: int
    prep_count: int
    prep_threshold: int
    treasury: int


class StormPrepOut(BaseModel):
    prep_count: int


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
        if row is None:
            raise HTTPException(status_code=404, detail="User not found.")
        if row["townId"]:
            raise HTTPException(status_code=409, detail="You are already in a town.")

        code = _generate_join_code()
        try:
            async with conn.transaction():
                town_row = await conn.fetchrow(
                    'INSERT INTO "Town" (name, "joinCode") VALUES ($1, $2) RETURNING id',
                    body.name, code,
                )
                result = await conn.execute(
                    'UPDATE "User" SET "townId" = $1 WHERE id = $2', town_row["id"], user_id,
                )
                if result == "UPDATE 0":
                    raise HTTPException(status_code=500, detail="Could not create town.")
                await conn.executemany(
                    'INSERT INTO "TownBuilding" ("townId", "buildingKey") VALUES ($1, $2)',
                    [(town_row["id"], key) for key in BUILDING_KEYS],
                )
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
        if row is None:
            raise HTTPException(status_code=404, detail="User not found.")
        if row["townId"]:
            raise HTTPException(status_code=409, detail="You are already in a town.")

        town_row = await conn.fetchrow('SELECT id FROM "Town" WHERE "joinCode" = $1', code)
        if not town_row:
            raise HTTPException(status_code=404, detail="Join code not found.")

        result = await conn.execute('UPDATE "User" SET "townId" = $1 WHERE id = $2', town_row["id"], user_id)
        if result == "UPDATE 0":
            raise HTTPException(status_code=500, detail="Could not join town.")
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
    except HTTPException:
        raise
    except asyncpg.PostgresError:
        logger.exception("Failed to load town")
        raise HTTPException(status_code=500, detail="Could not load town.")
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
