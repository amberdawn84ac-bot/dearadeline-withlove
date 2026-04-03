"""
Onboarding API — /api/onboarding/*

GET  /api/onboarding       — Fetch current student's complete profile
POST /api/onboarding       — Create/update student onboarding profile
PATCH /api/onboarding      — Update specific onboarding fields

Requires X-User-Id header (student ID) for authentication.
"""
import logging
import os
from typing import Optional

import asyncpg
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

_DSN = os.getenv("POSTGRES_DSN", "postgresql://adeline:adeline_local_dev@postgres:5432/hippocampus")


async def _get_conn():
    """Get a database connection."""
    return await asyncpg.connect(_DSN)


# ── Ensure User table has onboarding columns ──────────────────────────────────

_INIT_SQL = """
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "mathLevel" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "elaLevel" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "scienceLevel" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "historyLevel" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "interests" TEXT[] DEFAULT '{}';
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "learningStyle" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "pacingMultiplier" FLOAT DEFAULT 1.0;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "state" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "targetGraduationYear" INTEGER;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "onboardingComplete" BOOLEAN DEFAULT false;
"""


async def ensure_table() -> None:
    """Ensure all onboarding columns exist."""
    conn = await _get_conn()
    try:
        await conn.execute(_INIT_SQL)
    finally:
        await conn.close()


# ── Pydantic models ───────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    """Complete user profile response."""
    id: str
    name: str
    gradeLevel: Optional[str] = None
    mathLevel: Optional[str] = None
    elaLevel: Optional[str] = None
    scienceLevel: Optional[str] = None
    historyLevel: Optional[str] = None
    interests: list[str] = Field(default_factory=list)
    learningStyle: Optional[str] = None
    pacingMultiplier: float = Field(default=1.0)
    state: Optional[str] = None
    targetGraduationYear: Optional[int] = None
    onboardingComplete: bool = Field(default=False)


class OnboardingResponse(BaseModel):
    """API response wrapper."""
    ok: bool
    user: UserProfile


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=OnboardingResponse)
async def get_onboarding(x_user_id: str = Header(default="")):
    """
    Fetch current student's complete profile.

    Requires X-User-Id header containing the student ID.
    Returns 401 if not authenticated.
    Returns 404 if User not found.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized: X-User-Id header required")

    conn = await _get_conn()
    try:
        await conn.execute(_INIT_SQL)

        row = await conn.fetchrow(
            """
            SELECT
                "id", "name", "gradeLevel",
                "mathLevel", "elaLevel", "scienceLevel", "historyLevel",
                "interests", "learningStyle", "pacingMultiplier",
                "state", "targetGraduationYear", "onboardingComplete"
            FROM "User"
            WHERE "id" = $1
            """,
            x_user_id,
        )
    except Exception as e:
        logger.exception("[GET /api/onboarding] DB error")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    # Convert interests array (pgSQL array type) to Python list
    interests = list(row["interests"]) if row["interests"] else []

    user_profile = UserProfile(
        id=row["id"],
        name=row["name"],
        gradeLevel=row["gradeLevel"],
        mathLevel=row["mathLevel"],
        elaLevel=row["elaLevel"],
        scienceLevel=row["scienceLevel"],
        historyLevel=row["historyLevel"],
        interests=interests,
        learningStyle=row["learningStyle"],
        pacingMultiplier=row["pacingMultiplier"] or 1.0,
        state=row["state"],
        targetGraduationYear=row["targetGraduationYear"],
        onboardingComplete=row["onboardingComplete"],
    )

    return OnboardingResponse(ok=True, user=user_profile)
