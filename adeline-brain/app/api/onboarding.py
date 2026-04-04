"""
Onboarding API — /api/onboarding/*

GET  /api/onboarding       — Fetch current student's complete profile
POST /api/onboarding       — Create/update student onboarding profile
PATCH /api/onboarding      — Update specific onboarding fields

Requires Authorization header with Bearer token for authentication.
"""
import logging
import os
from datetime import datetime
from typing import Optional

import asyncpg
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field, validator

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

# Valid US state names for validation
_VALID_STATES = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
    'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
    'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
    'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
    'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
    'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
    'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
    'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
    'West Virginia', 'Wisconsin', 'Wyoming'
]


class OnboardingRequest(BaseModel):
    """Initial onboarding submission request."""
    name: str
    gradeLevel: str
    interests: list[str]
    learningStyle: str
    state: str
    targetGraduationYear: int
    coppaConsent: bool

    @validator('name')
    def validate_name(cls, v):
        """Validate that name is non-empty."""
        if not v or not v.strip():
            raise ValueError('name is required and cannot be empty')
        return v.strip()

    @validator('gradeLevel')
    def validate_grade(cls, v):
        """Validate that gradeLevel is K or 1-12."""
        valid_grades = ['K'] + [str(i) for i in range(1, 13)]
        if v not in valid_grades:
            raise ValueError('gradeLevel must be K or 1-12')
        return v

    @validator('learningStyle')
    def validate_learning_style(cls, v):
        """Validate that learningStyle is EXPEDITION or CLASSIC."""
        if v not in ['EXPEDITION', 'CLASSIC']:
            raise ValueError('learningStyle must be EXPEDITION or CLASSIC')
        return v

    @validator('state')
    def validate_state(cls, v):
        """Validate that state is a valid US state name."""
        if v not in _VALID_STATES:
            raise ValueError(f'{v} is not a valid US state')
        return v

    @validator('targetGraduationYear')
    def validate_year(cls, v):
        """Validate that targetGraduationYear is between current year and current year+20."""
        current_year = datetime.now().year
        if v < current_year or v > current_year + 20:
            raise ValueError(f'targetGraduationYear must be between {current_year} and {current_year + 20}')
        return v

    @validator('interests')
    def validate_interests(cls, v):
        """Validate that interests has at least 1 item."""
        if not v or len(v) == 0:
            raise ValueError('interests must include at least one item')
        return v

    @validator('coppaConsent')
    def validate_coppa(cls, v):
        """Validate that COPPA consent is given."""
        if not v:
            raise ValueError('COPPA consent is required')
        return v


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


@router.post("/", response_model=OnboardingResponse)
async def post_onboarding(
    request: OnboardingRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Initial onboarding submission (first-time setup after signup).

    Validates all required fields and COPPA consent.
    Updates User record with profile and sets onboardingComplete=true.

    Required fields:
    - name: Student's full name (required, non-empty)
    - gradeLevel: K or 1-12
    - interests: Array with at least 1 item
    - learningStyle: EXPEDITION or CLASSIC
    - state: Valid US state name
    - targetGraduationYear: 4 digits, between current year and current year+20
    - coppaConsent: Must be true (COPPA compliance required)

    Returns updated user profile with onboardingComplete=true.
    """
    user_id = _get_user_id_from_auth(authorization)

    conn = await _get_conn()
    try:
        # Update User with onboarding profile
        await conn.execute(
            """
            UPDATE "User"
            SET
                "name" = $2,
                "gradeLevel" = $3,
                "interests" = $4::TEXT[],
                "learningStyle" = $5,
                "state" = $6,
                "targetGraduationYear" = $7,
                "onboardingComplete" = true,
                "updatedAt" = NOW()
            WHERE "id" = $1
            """,
            user_id,
            request.name,
            request.gradeLevel,
            request.interests,
            request.learningStyle,
            request.state,
            request.targetGraduationYear,
        )

        # Fetch updated user profile
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
        logger.exception("[POST /api/onboarding] DB error")
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

    logger.info(f"[POST /api/onboarding] User {user_id} completed onboarding: {request.name}, grade {request.gradeLevel}")

    return OnboardingResponse(ok=True, user=user_profile)
