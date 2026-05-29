"""
Students API — /students/*

Student profile CRUD with Supabase JWT authentication.

POST /students/register    — Upsert a student profile (uses JWT sub as student ID)
GET  /students/{student_id}          — Fetch profile (ownership verified)
GET  /students/{student_id}/state    — Full StudentState (ownership verified)
"""
import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.api.middleware import get_current_user_id, verify_student_access

from app.models.student import load_student_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/students", tags=["students"])



async def _get_conn():
    from app.config import get_db_conn
    return await get_db_conn()


# ── Ensure student_profiles table exists ─────────────────────────────────────

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS student_profiles (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL DEFAULT '',
    email        TEXT UNIQUE,
    grade_level  TEXT NOT NULL DEFAULT 'K',
    is_homestead BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def ensure_table() -> None:
    conn = await _get_conn()
    try:
        await conn.execute(_INIT_SQL)
    finally:
        await conn.close()


# ── Pydantic models ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name:         str = Field(default="", max_length=200)
    email:        str | None = Field(default=None)
    grade_level:  str = Field(default="K", pattern=r"^(K|[1-9]|1[0-2])$")
    is_homestead: bool = Field(default=False)


class StudentProfile(BaseModel):
    student_id:   str
    name:         str
    email:        str | None
    grade_level:  str
    is_homestead: bool
    created_at:   str
    updated_at:   str


class StudentStateResponse(BaseModel):
    student_id:  str
    grade_level: str
    is_homestead: bool
    tracks: dict  # track_name → {mastery_score, mastery_band, lesson_count}


# ── Routes ────────────────────────────────────────────────────────────────────

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


@router.get("/{student_id}/state", response_model=StudentStateResponse)
async def get_student_state(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
):
    """
    Return the full StudentState (mastery scores, bands, lesson counts per track).
    Used by ZPDRecommendations in the UI.
    """
    # Fetch profile for grade_level + is_homestead
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


# ── POST /students/{student_id}/modality-preference ───────────────────────────

_VALID_MODALITIES = {"visual", "auditory", "kinesthetic", "reading"}

class ModalityPreferenceRequest(BaseModel):
    modality: str = Field(..., description="visual | auditory | kinesthetic | reading")


@router.post("/{student_id}/modality-preference")
async def save_modality_preference(
    student_id: str,
    body: ModalityPreferenceRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Save the student's explicit modality preference to the User table.

    This immediately overrides behavioral inference from LearningRecord rows.
    The learner_profiler will use this as the seed modality on the next lesson,
    then refine it over time as interaction data accumulates.
    """
    await verify_student_access(student_id, current_user_id)

    modality = body.modality.lower().strip()
    if modality not in _VALID_MODALITIES:
        raise HTTPException(
            status_code=400,
            detail=f"modality must be one of: {', '.join(sorted(_VALID_MODALITIES))}",
        )

    conn = await _get_conn()
    try:
        result = await conn.execute(
            'UPDATE "User" SET "learningStyle" = $1, "updatedAt" = NOW() WHERE "id" = $2',
            modality,
            student_id,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Student not found")
        logger.info(f"[Students] Modality preference saved: student={student_id} modality={modality}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Students] Failed to save modality preference: {e}")
        raise HTTPException(status_code=500, detail="Failed to save preference")
    finally:
        await conn.close()

    return {"ok": True, "modality": modality}
