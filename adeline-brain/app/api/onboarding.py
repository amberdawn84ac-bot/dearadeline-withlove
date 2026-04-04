"""
Onboarding API — /api/onboarding

Student profile CRUD for onboarding and settings updates.

GET  /api/onboarding            — Fetch current student profile (authenticated)
POST /api/onboarding            — Complete initial onboarding (first-time setup)
PATCH /api/onboarding           — Update student profile from Settings page
"""
import logging
import os
from datetime import datetime
from typing import Optional

import asyncpg
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

_DSN = os.getenv("POSTGRES_DSN", "postgresql://adeline:adeline_local_dev@postgres:5432/hippocampus")

# US States for validation (alphabetical)
_VALID_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming", "District of Columbia"
}


async def _get_conn():
    """Get a PostgreSQL connection."""
    return await asyncpg.connect(_DSN)


def _get_user_id_from_auth(authorization: Optional[str]) -> str:
    """
    Extract user ID from Authorization Bearer token.

    For now, we use the token value as the user ID directly.
    In production, this would validate a JWT.

    Raises HTTPException(401) if token is missing or invalid.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty Authorization token")

    return token


# ── Pydantic models ──────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    """Student profile response model."""
    id: str
    name: str
    gradeLevel: str
    mathLevel: Optional[int] = None
    elaLevel: Optional[int] = None
    scienceLevel: Optional[int] = None
    historyLevel: Optional[int] = None
    interests: list[str]
    learningStyle: Optional[str] = None
    pacingMultiplier: float = 1.0
    state: Optional[str] = None
    targetGraduationYear: Optional[int] = None
    onboardingComplete: bool = False


class OnboardingResponse(BaseModel):
    """Response wrapper for onboarding endpoints."""
    ok: bool
    user: UserProfile


class OnboardingRequest(BaseModel):
    """Initial onboarding request (POST)."""
    name: str
    gradeLevel: str
    interests: list[str]
    learningStyle: str
    state: str
    targetGraduationYear: int
    coppaConsent: bool

    @validator("name")
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("name is required")
        if len(v) > 200:
            raise ValueError("name must be <= 200 characters")
        return v.strip()

    @validator("gradeLevel")
    def validate_grade(cls, v):
        valid_grades = ["K"] + [str(i) for i in range(1, 13)]
        if v not in valid_grades:
            raise ValueError("gradeLevel must be K or 1-12")
        return v

    @validator("learningStyle")
    def validate_learning_style(cls, v):
        if v not in ["EXPEDITION", "CLASSIC"]:
            raise ValueError("learningStyle must be EXPEDITION or CLASSIC")
        return v

    @validator("state")
    def validate_state(cls, v):
        if v not in _VALID_STATES:
            raise ValueError(f"'{v}' is not a valid US state")
        return v

    @validator("targetGraduationYear")
    def validate_year(cls, v):
        current_year = datetime.now().year
        if v < current_year or v > current_year + 20:
            raise ValueError(f"targetGraduationYear must be between {current_year} and {current_year + 20}")
        return v

    @validator("interests")
    def validate_interests(cls, v):
        if not v or len(v) == 0:
            raise ValueError("interests must include at least one item")
        if any(not s or not isinstance(s, str) for s in v):
            raise ValueError("interests must be non-empty strings")
        return v

    @validator("coppaConsent")
    def validate_coppa(cls, v):
        if not v:
            raise ValueError("coppaConsent must be true")
        return v


class SettingsUpdateRequest(BaseModel):
    """Settings update request (all fields optional, PATCH)."""
    gradeLevel: Optional[str] = None
    mathLevel: Optional[int] = None
    elaLevel: Optional[int] = None
    scienceLevel: Optional[int] = None
    historyLevel: Optional[int] = None
    interests: Optional[list[str]] = None
    learningStyle: Optional[str] = None
    pacingMultiplier: Optional[float] = None
    state: Optional[str] = None
    targetGraduationYear: Optional[int] = None

    @validator("gradeLevel", pre=True, always=False)
    def validate_grade(cls, v):
        if v is None:
            return v
        valid_grades = ["K"] + [str(i) for i in range(1, 13)]
        if v not in valid_grades:
            raise ValueError("gradeLevel must be K or 1-12")
        return v

    @validator("learningStyle", pre=True, always=False)
    def validate_learning_style(cls, v):
        if v is None:
            return v
        if v not in ["EXPEDITION", "CLASSIC"]:
            raise ValueError("learningStyle must be EXPEDITION or CLASSIC")
        return v

    @validator("state", pre=True, always=False)
    def validate_state(cls, v):
        if v is None:
            return v
        if v not in _VALID_STATES:
            raise ValueError(f"'{v}' is not a valid US state")
        return v

    @validator("targetGraduationYear", pre=True, always=False)
    def validate_year(cls, v):
        if v is None:
            return v
        current_year = datetime.now().year
        if v < current_year or v > current_year + 20:
            raise ValueError(f"targetGraduationYear must be between {current_year} and {current_year + 20}")
        return v

    @validator("interests", pre=True, always=False)
    def validate_interests(cls, v):
        if v is None:
            return v
        if not v or len(v) == 0:
            raise ValueError("interests must include at least one item")
        if any(not s or not isinstance(s, str) for s in v):
            raise ValueError("interests must be non-empty strings")
        return v

    @validator("mathLevel", "elaLevel", "scienceLevel", "historyLevel", pre=True, always=False)
    def validate_subject_level(cls, v):
        if v is None:
            return v
        if not isinstance(v, int) or v < 0 or v > 12:
            raise ValueError("Subject level must be 0-12 (0=K, 12=12th grade)")
        return v

    @validator("pacingMultiplier", pre=True, always=False)
    def validate_pacing(cls, v):
        if v is None:
            return v
        valid = [1.0, 1.25, 1.5, 2.0]
        if v not in valid:
            raise ValueError(f"pacingMultiplier must be one of {valid}")
        return v


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=OnboardingResponse)
async def get_onboarding(authorization: Optional[str] = Header(None)):
    """
    Fetch current student profile (used by Settings page on load).

    Requires Authorization Bearer token.

    Returns:
    - 200: User profile with all fields
    - 401: Missing or invalid Authorization header
    - 404: User not found
    - 500: Database error
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

    # Convert interests array (PostgreSQL array type) to Python list
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

    logger.info(f"[GET /api/onboarding] Fetched profile for user {user_id}")

    return OnboardingResponse(ok=True, user=user_profile)


@router.post("/", response_model=OnboardingResponse, status_code=201)
async def post_onboarding(request: OnboardingRequest):
    """
    Complete initial onboarding (first-time setup after signup).

    Validates all required fields and COPPA consent, then creates/updates
    User record with onboardingComplete = true.

    Request body must include:
    - name: student name (required)
    - gradeLevel: K or 1-12 (required)
    - interests: array with at least 1 item (required)
    - learningStyle: EXPEDITION or CLASSIC (required)
    - state: valid US state name (required)
    - targetGraduationYear: 4-digit year in reasonable range (required)
    - coppaConsent: must be true (required)

    Returns:
    - 201: User profile with onboardingComplete = true
    - 400: Validation error
    - 500: Database error
    """
    conn = await _get_conn()
    try:
        # For now, assume the student ID is passed separately or generated.
        # In production, this would come from the authenticated session.
        # For demo, we'll generate a UUID.
        import uuid
        user_id = str(uuid.uuid4())

        row = await conn.fetchrow(
            """
            INSERT INTO "User" (
                "id", "name", "gradeLevel", "interests", "learningStyle",
                "state", "targetGraduationYear", "onboardingComplete"
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, true)
            ON CONFLICT ("id") DO UPDATE SET
                "name" = EXCLUDED."name",
                "gradeLevel" = EXCLUDED."gradeLevel",
                "interests" = EXCLUDED."interests",
                "learningStyle" = EXCLUDED."learningStyle",
                "state" = EXCLUDED."state",
                "targetGraduationYear" = EXCLUDED."targetGraduationYear",
                "onboardingComplete" = true,
                "updatedAt" = NOW()
            RETURNING
                "id", "name", "gradeLevel",
                "mathLevel", "elaLevel", "scienceLevel", "historyLevel",
                "interests", "learningStyle", "pacingMultiplier",
                "state", "targetGraduationYear", "onboardingComplete"
            """,
            user_id, request.name, request.gradeLevel, request.interests,
            request.learningStyle, request.state, request.targetGraduationYear,
        )
    except Exception as e:
        logger.exception("[POST /api/onboarding] DB error")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

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

    logger.info(
        f"[Onboarding] User {user_id} completed onboarding: {request.name}, "
        f"grade {request.gradeLevel}, interests {request.interests}"
    )

    return OnboardingResponse(ok=True, user=user_profile)


@router.patch("/", response_model=OnboardingResponse)
async def patch_onboarding(
    request: SettingsUpdateRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Update student profile from Settings page (authenticated student only).

    All fields are optional. Only provided fields are updated.

    Validates each field if provided:
    - gradeLevel: K or 1-12
    - mathLevel/elaLevel/scienceLevel/historyLevel: 0-12 (0=K, null=use gradeLevel)
    - interests: array with at least 1 item
    - learningStyle: EXPEDITION or CLASSIC
    - pacingMultiplier: 1.0, 1.25, 1.5, or 2.0
    - state: valid US state
    - targetGraduationYear: 4 digits, reasonable range

    Future: Clear any cached journey plan or learning state (Adeline must
    recompute with new profile) when cache table is implemented.

    Returns:
    - 200: Updated user profile
    - 400: Validation error
    - 401: Missing or invalid Authorization header
    - 404: User not found
    - 500: Database error
    """
    user_id = _get_user_id_from_auth(authorization)

    conn = await _get_conn()
    try:
        # Build dynamic UPDATE query with only non-null fields
        updates = []
        params = [user_id]
        param_index = 2

        if request.gradeLevel is not None:
            updates.append(f'"gradeLevel" = ${param_index}')
            params.append(request.gradeLevel)
            param_index += 1

        if request.mathLevel is not None:
            updates.append(f'"mathLevel" = ${param_index}')
            params.append(request.mathLevel)
            param_index += 1

        if request.elaLevel is not None:
            updates.append(f'"elaLevel" = ${param_index}')
            params.append(request.elaLevel)
            param_index += 1

        if request.scienceLevel is not None:
            updates.append(f'"scienceLevel" = ${param_index}')
            params.append(request.scienceLevel)
            param_index += 1

        if request.historyLevel is not None:
            updates.append(f'"historyLevel" = ${param_index}')
            params.append(request.historyLevel)
            param_index += 1

        if request.interests is not None:
            updates.append(f'"interests" = ${param_index}::TEXT[]')
            params.append(request.interests)
            param_index += 1

        if request.learningStyle is not None:
            updates.append(f'"learningStyle" = ${param_index}')
            params.append(request.learningStyle)
            param_index += 1

        if request.pacingMultiplier is not None:
            updates.append(f'"pacingMultiplier" = ${param_index}')
            params.append(request.pacingMultiplier)
            param_index += 1

        if request.state is not None:
            updates.append(f'"state" = ${param_index}')
            params.append(request.state)
            param_index += 1

        if request.targetGraduationYear is not None:
            updates.append(f'"targetGraduationYear" = ${param_index}')
            params.append(request.targetGraduationYear)
            param_index += 1

        # Always update timestamp
        updates.append('"updatedAt" = NOW()')

        if updates:
            # Build and execute UPDATE with dynamic fields
            update_query = f"""
                UPDATE "User"
                SET {', '.join(updates)}
                WHERE "id" = $1
                RETURNING
                    "id", "name", "gradeLevel",
                    "mathLevel", "elaLevel", "scienceLevel", "historyLevel",
                    "interests", "learningStyle", "pacingMultiplier",
                    "state", "targetGraduationYear", "onboardingComplete"
            """
            row = await conn.fetchrow(update_query, *params)
        else:
            # No fields to update, just fetch current profile
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
        logger.exception("[PATCH /api/onboarding] DB error")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    # Convert interests array (PostgreSQL array type) to Python list
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

    logger.info(f"[PATCH /api/onboarding] User {user_id} updated profile")

    return OnboardingResponse(ok=True, user=user_profile)
