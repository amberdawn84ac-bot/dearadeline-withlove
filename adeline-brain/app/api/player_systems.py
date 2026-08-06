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
