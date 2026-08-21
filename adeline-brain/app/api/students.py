"""
Students API — /students/*

Student profile CRUD with Supabase JWT authentication.

POST /students/register    — Upsert a student profile (uses JWT sub as student ID)
GET  /students/{student_id}          — Fetch profile (ownership verified)
GET  /students/{student_id}/state    — Full StudentState (ownership verified)
"""
import json
import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.api.middleware import get_current_user_id, verify_student_access, require_role, require_account_role
from app.api.student_auth import load_student_user, StudentUserOut
from app.schemas.api_models import UserRole

from app.models.student import load_student_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/students", tags=["students"])
limiter = Limiter(key_func=get_remote_address)



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


# ── POST /students/{student_id}/lesson-rating ─────────────────────────────────

class LessonRatingRequest(BaseModel):
    lessonId:      str = Field(..., description="ID of the lesson being rated")
    componentType: str = Field(..., description="Primary component type shown in the lesson")
    rating:        int = Field(..., description="1 = liked, -1 = did not like")
    track:         str | None = None
    topic:         str | None = None


@router.post("/{student_id}/lesson-rating")
async def save_lesson_rating(
    student_id: str,
    body: LessonRatingRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Save a thumbs-up / thumbs-down rating for a lesson.

    Ratings are stored in ComponentRating and read back by the component
    selector on future lessons — components rated up get picked more often,
    components rated down get deprioritized.
    """
    await verify_student_access(student_id, current_user_id)

    if body.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="rating must be 1 or -1")

    conn = await _get_conn()
    try:
        await conn.execute(
            """
            INSERT INTO "ComponentRating"
                ("studentId", "lessonId", "componentType", "rating", "track", "topic")
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT DO NOTHING
            """,
            student_id,
            body.lessonId,
            body.componentType,
            body.rating,
            body.track,
            body.topic,
        )
        logger.info(
            f"[Students] Lesson rating saved: student={student_id} "
            f"component={body.componentType} rating={body.rating}"
        )
    except Exception as e:
        logger.error(f"[Students] Failed to save lesson rating: {e}")
        raise HTTPException(status_code=500, detail="Failed to save rating")
    finally:
        await conn.close()

    return {"ok": True}


# ── Mobile profile / XP / coins / season-pass ─────────────────────────────────

class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    avatar_data: dict | None = None
    grade_level: str | None = None


class XPCoinsDelta(BaseModel):
    delta: int


class XPResponse(BaseModel):
    xp: int


class CoinsResponse(BaseModel):
    ade_coins: int


class SeasonPassResponse(BaseModel):
    claimed_tiers: list[int]


class UpdateSeasonPassRequest(BaseModel):
    claimed_tiers: list[int]


class ClaimStudentRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class ClaimStudentResponse(BaseModel):
    student_id: str
    display_name: str
    username: str
    xp: int
    grade_level: str


@router.get("/{student_id}/profile", response_model=StudentUserOut)
async def get_student_profile(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
):
    conn = await _get_conn()
    try:
        user = await load_student_user(conn, student_id)
    except asyncpg.PostgresError:
        logger.exception("[/students/{id}/profile] DB error")
        raise HTTPException(status_code=500, detail="A database error occurred.")
    finally:
        await conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
    return user


@router.patch("/{student_id}/profile", response_model=StudentUserOut)
async def update_student_profile(
    student_id: str,
    body: UpdateProfileRequest,
    _user_id: str = Depends(verify_student_access),
):
    conn = await _get_conn()
    try:
        async with conn.transaction():
            if body.display_name is not None:
                await conn.execute('UPDATE "User" SET name = $1 WHERE id = $2', body.display_name, student_id)
            if body.avatar_data is not None:
                await conn.execute(
                    'UPDATE "User" SET "avatarData" = $1::jsonb WHERE id = $2',
                    json.dumps(body.avatar_data), student_id,
                )
            if body.grade_level is not None:
                await conn.execute('UPDATE "User" SET "gradeLevel" = $1 WHERE id = $2', body.grade_level, student_id)
        user = await load_student_user(conn, student_id)
    except asyncpg.PostgresError:
        logger.exception("[/students/{id}/profile PATCH] DB error")
        raise HTTPException(status_code=500, detail="A database error occurred.")
    finally:
        await conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
    return user


@router.patch("/{student_id}/xp", response_model=XPResponse)
async def patch_xp(
    student_id: str,
    body: XPCoinsDelta,
    _user_id: str = Depends(verify_student_access),
):
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            'UPDATE "User" SET xp = xp + $1 WHERE id = $2 RETURNING xp',
            body.delta, student_id,
        )
    except asyncpg.PostgresError:
        logger.exception("[/students/{id}/xp] DB error")
        raise HTTPException(status_code=500, detail="A database error occurred.")
    finally:
        await conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    return XPResponse(xp=row["xp"])


@router.patch("/{student_id}/coins", response_model=CoinsResponse)
async def patch_coins(
    student_id: str,
    body: XPCoinsDelta,
    _user_id: str = Depends(verify_student_access),
):
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            'UPDATE "User" SET "adeCoins" = "adeCoins" + $1 WHERE id = $2 RETURNING "adeCoins"',
            body.delta, student_id,
        )
    except asyncpg.PostgresError:
        logger.exception("[/students/{id}/coins] DB error")
        raise HTTPException(status_code=500, detail="A database error occurred.")
    finally:
        await conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    return CoinsResponse(ade_coins=row["adeCoins"])


@router.get("/{student_id}/season-pass", response_model=SeasonPassResponse)
async def get_season_pass(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
):
    conn = await _get_conn()
    try:
        row = await conn.fetchrow('SELECT "seasonPass" FROM "User" WHERE id = $1', student_id)
    except asyncpg.PostgresError:
        logger.exception("[/students/{id}/season-pass] DB error")
        raise HTTPException(status_code=500, detail="A database error occurred.")
    finally:
        await conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    season_pass = json.loads(row["seasonPass"]) if row["seasonPass"] else {}
    return SeasonPassResponse(claimed_tiers=season_pass.get("claimed_tiers", []))


@router.patch("/{student_id}/season-pass", response_model=SeasonPassResponse)
async def update_season_pass(
    student_id: str,
    body: UpdateSeasonPassRequest,
    _user_id: str = Depends(verify_student_access),
):
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            'UPDATE "User" SET "seasonPass" = $1::jsonb WHERE id = $2 RETURNING "seasonPass"',
            json.dumps({"claimed_tiers": body.claimed_tiers}), student_id,
        )
    except asyncpg.PostgresError:
        logger.exception("[/students/{id}/season-pass PATCH] DB error")
        raise HTTPException(status_code=500, detail="A database error occurred.")
    finally:
        await conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    return SeasonPassResponse(claimed_tiers=json.loads(row["seasonPass"])["claimed_tiers"])


@router.post("/claim", response_model=ClaimStudentResponse)
@limiter.limit("10/minute")
async def claim_student(
    request: Request,
    body: ClaimStudentRequest,
    parent_id: str = Depends(get_current_user_id),
    _role: str = Depends(require_account_role(UserRole.PARENT, UserRole.ADMIN)),
):
    code = body.code.strip().upper()
    conn = await _get_conn()
    try:
        student = await conn.fetchrow(
            'SELECT id, name, username, xp, "gradeLevel", "parentId" FROM "User" WHERE "linkCode" = $1',
            code,
        )
        if not student:
            raise HTTPException(status_code=404, detail="Link code not found.")

        result = await conn.fetchrow(
            'UPDATE "User" SET "parentId" = $1, "updatedAt" = NOW() WHERE id = $2 AND role = \'STUDENT\' AND ("parentId" IS NULL OR "parentId" = $1) RETURNING id',
            parent_id, student["id"],
        )
        if not result:
            raise HTTPException(status_code=409, detail="This code is already claimed by another parent.")
    except asyncpg.PostgresError:
        logger.exception("[/students/claim] DB error")
        raise HTTPException(status_code=500, detail="A database error occurred.")
    finally:
        await conn.close()

    # Linking changes the household-wide investigation identity immediately.
    try:
        from app.connections.redis_client import redis_client
        await redis_client.delete(f"learning_plan:v6:{student['id']}")
    except Exception as exc:
        logger.warning("Could not invalidate claimed student's plan cache: %s", exc)

    return ClaimStudentResponse(
        student_id=student["id"],
        display_name=student["name"],
        username=student["username"] or "",
        xp=student["xp"],
        grade_level=student["gradeLevel"] or "K-2",
    )
