"""
Student auth — /auth/student/*

Username + 4-digit PIN accounts for Adelinemobile. These are plain rows in
the existing "User" table (role=STUDENT) with no Supabase Auth signup —
login/register here mint an HS256 JWT signed with SUPABASE_JWT_SECRET, which
the existing auth middleware (app/api/middleware.py::_decode_jwt) already
accepts as its HS256 fallback path. Every other brain endpoint that depends
on get_current_user_id / verify_student_access therefore works unmodified
for these tokens.
"""
import json
import hashlib
import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import STUDENT_JWT_SECRET, get_db_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/student", tags=["student-auth"])
limiter = Limiter(key_func=get_remote_address)

TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


# ── Request / response models ─────────────────────────────────────────────────

class StudentRegisterRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-z0-9_]+$")
    pin: str = Field(..., min_length=4, max_length=4, pattern=r"^[0-9]{4}$")
    grade_level: str = Field(default="K-2")
    parent_name: str = Field(..., min_length=1, max_length=100)
    parent_email: str = Field(..., min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    parent_verification_token: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]+$")


class StudentLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=20)
    pin: str = Field(..., min_length=4, max_length=4, pattern=r"^[0-9]{4}$")


class StudentUserOut(BaseModel):
    id: str
    display_name: str
    username: str
    xp: int
    ade_coins: int
    avatar_data: dict
    grade_level: str
    link_code: str
    parent_id: str | None
    parent_display_name: str | None
    town_id: str | None
    reputation: int


class StudentAuthResponse(BaseModel):
    token: str | None = None
    student_id: str
    user: StudentUserOut
    requires_parent_verification: bool = False


# ── Helpers ────────────────────────────────────────────────────────────────────

def mint_student_token(user_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "app_metadata": {"role": "STUDENT"},
    }
    return jwt.encode(payload, STUDENT_JWT_SECRET, algorithm="HS256")


async def load_student_user(conn: asyncpg.Connection, user_id: str) -> StudentUserOut | None:
    """
    Load a student through a JSON snapshot of the User row.

    Adelinemobile databases may be at different migration levels. Reading the
    row as JSON keeps optional profile fields from turning a valid login into a
    500 response when an older database does not have one of those columns yet.
    """
    row = await conn.fetchrow(
        """
        SELECT to_jsonb(u) AS profile
        FROM "User" u
        WHERE u.id = $1
        """,
        user_id,
    )
    if not row:
        return None

    profile_raw = row["profile"]
    if isinstance(profile_raw, dict):
        profile = profile_raw
    elif isinstance(profile_raw, str):
        try:
            profile = json.loads(profile_raw)
        except (TypeError, ValueError):
            logger.exception("Invalid User JSON for student %s", user_id)
            return None
    else:
        logger.error("Unexpected User JSON type for student %s: %s", user_id, type(profile_raw).__name__)
        return None

    # Never let a parent Supabase session be projected as a learner profile.
    if str(profile.get("role") or "").upper() != "STUDENT":
        return None

    # Transparently retire the old UUID-derived six-character credentials when
    # an unlinked learner next signs in or opens their profile.
    current_link_code = str(profile.get("linkCode") or "")
    if not profile.get("parentId") and len(current_link_code) < 12:
        replacement = secrets.token_hex(6).upper()
        try:
            await conn.execute(
                'UPDATE "User" SET "linkCode" = $1, "updatedAt" = NOW() WHERE id = $2',
                replacement, user_id,
            )
            profile["linkCode"] = replacement
        except asyncpg.UniqueViolationError:
            logger.warning("Link-code collision while upgrading student %s; retaining current code", user_id)

    avatar_raw = profile.get("avatarData")
    if isinstance(avatar_raw, dict):
        avatar_data = avatar_raw
    elif isinstance(avatar_raw, str) and avatar_raw:
        try:
            avatar_data = json.loads(avatar_raw)
        except (TypeError, ValueError):
            logger.warning("Invalid avatarData JSON for student %s; using empty avatar", user_id)
            avatar_data = {}
    else:
        avatar_data = {}

    parent_id_raw = profile.get("parentId")
    parent_display_name = None
    if parent_id_raw:
        parent_display_name = await conn.fetchval(
            """SELECT name FROM "User" WHERE id = $1""",
            str(parent_id_raw),
        )

    def as_int(value, default=0):
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    return StudentUserOut(
        id=str(profile.get("id") or user_id),
        display_name=str(profile.get("name") or ""),
        username=str(profile.get("username") or ""),
        xp=as_int(profile.get("xp")),
        ade_coins=as_int(profile.get("adeCoins")),
        avatar_data=avatar_data,
        grade_level=str(profile.get("gradeLevel") or "K-2"),
        link_code=str(profile.get("linkCode") or ""),
        parent_id=str(parent_id_raw) if parent_id_raw else None,
        parent_display_name=parent_display_name,
        town_id=str(profile.get("townId")) if profile.get("townId") is not None else None,
        reputation=as_int(profile.get("reputation")),
    )


async def _ensure_student_profiles_row(conn: asyncpg.Connection, user_id: str, name: str, grade_level: str) -> None:
    """
    Insert row into the legacy `student_profiles` table (see
    app/api/students.py::_INIT_SQL) so lesson generation / mastery tracking
    (which reads student_profiles, not User) keeps working for kids who
    register through this endpoint instead of the old /students/register.

    The caller must ensure the table exists before calling this.
    """
    await conn.execute(
        """
        INSERT INTO student_profiles (id, name, grade_level, is_homestead)
        VALUES ($1, $2, $3, TRUE)
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, grade_level = EXCLUDED.grade_level
        """,
        user_id, name, grade_level,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=StudentAuthResponse)
@limiter.limit("5/minute;30/hour")
async def register_student_account(request: Request, body: StudentRegisterRequest):
    user_id = str(uuid.uuid4())
    # This is an invitation credential, not a display identifier.  Do not derive
    # it from the student's UUID: that made old six-character codes guessable.
    link_code = secrets.token_hex(6).upper()
    pin_hash = bcrypt.hashpw(body.pin.encode(), bcrypt.gensalt()).decode()
    placeholder_email = f"{body.username}@mobile.adelineworld.local"
    consent_token_hash = hashlib.sha256(body.parent_verification_token.encode("utf-8")).hexdigest()
    consent_expires = datetime.now(timezone.utc) + timedelta(hours=72)

    conn = await get_db_conn()
    try:
        # Both INSERTs in a transaction for atomicity
        async with conn.transaction():
            try:
                await conn.execute(
                    """
                    INSERT INTO "User"
                        (id, name, email, role, "isHomestead", "gradeLevel",
                         username, "pinHash", "linkCode", xp, "adeCoins",
                         "parentName", "parentEmail", "coppaVerified",
                         "coppaPendingToken", "coppaTokenExpiresAt")
                    VALUES ($1, $2, $3, 'STUDENT', TRUE, $4, $5, $6, $7, 0, 0, $8, $9, FALSE, $10, $11)
                    """,
                    user_id, body.display_name, placeholder_email, body.grade_level,
                    body.username, pin_hash, link_code, body.parent_name.strip(), body.parent_email.strip().lower(),
                    consent_token_hash, consent_expires,
                )
            except asyncpg.UniqueViolationError as e:
                # Both username and the derived placeholder email represent the
                # same player identity. Old partial registrations may collide on
                # either constraint, so report the real remedy.
                constraint = (e.constraint_name or "").lower()
                if "linkcode" in constraint or "link_code" in constraint:
                    logger.warning("Rare link-code collision during registration; user may retry")
                    raise HTTPException(status_code=409, detail="We could not reserve a link code. Please try once more.")
                logger.info("Player identity already exists during registration (constraint=%s)", e.constraint_name)
                raise HTTPException(status_code=409, detail="That player name is already in use. Try adding a last initial.")
            except asyncpg.PostgresError:
                logger.exception("Database error during student registration")
                raise HTTPException(status_code=500, detail="Registration failed.")

            await _ensure_student_profiles_row(conn, user_id, body.display_name, body.grade_level)

        user = await load_student_user(conn, user_id)
    finally:
        await conn.close()

    if not user:
        raise HTTPException(status_code=500, detail="Registration failed.")
    # Do not mint a usable student session until guardian approval. The raw
    # one-time token exists only in the Next.js server that delivers the email.
    return StudentAuthResponse(student_id=user_id, user=user, requires_parent_verification=True)


@router.post("/login")
@limiter.limit("5/minute;30/hour")
async def login_student(request: Request, body: StudentLoginRequest):
    username = body.username.strip().lower()
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            """SELECT id, "pinHash", "parentId", "coppaVerified" FROM "User" WHERE username = $1 AND role = 'STUDENT'""",
            username,
        )
        if not row or not row["pinHash"] or not bcrypt.checkpw(body.pin.encode(), row["pinHash"].encode()):
            raise HTTPException(status_code=401, detail="Username or PIN is incorrect.")
        if not row["parentId"] and not row["coppaVerified"]:
            raise HTTPException(status_code=403, detail="A parent or guardian must approve this learner account before sign in.")
        student_id = str(row["id"])
        user = await load_student_user(conn, student_id)
    finally:
        await conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="Student profile was not found.")
    token = mint_student_token(student_id)
    return StudentAuthResponse(token=token, student_id=student_id, user=user)
