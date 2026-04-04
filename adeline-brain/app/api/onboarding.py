"""
Onboarding API — /api/onboarding/*

GET  /api/onboarding       — Fetch current student's complete profile
POST /api/onboarding       — Create/update student onboarding profile
PATCH /api/onboarding      — Update specific onboarding fields

Requires Authorization header with Bearer token for authentication.
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


def _get_user_id_from_auth(authorization: Optional[str]) -> str:
    """Extract user ID from Authorization header (Bearer {user_id})."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    return parts[1]


# ── Pydantic models ───────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    """Complete user profile response."""
    id: str
    name: str
    gradeLevel: Optional[str] = None
    mathLevel: Optional[int] = None
    elaLevel: Optional[int] = None
    scienceLevel: Optional[int] = None
    historyLevel: Optional[int] = None
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
async def get_onboarding(authorization: Optional[str] = Header(None)):
    """
    Fetch current student's complete profile.

    Requires Authorization header with Bearer token.
    Returns 401 if not authenticated.
    Returns 404 if User not found.
    """
    user_id = _get_user_id_from_auth(authorization)

    conn = await _get_conn()
    try:
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
            user_id,
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
