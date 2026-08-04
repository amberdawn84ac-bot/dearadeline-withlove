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
import logging
import time
import uuid

import asyncpg
import bcrypt
import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import SUPABASE_JWT_SECRET, get_db_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/student", tags=["student-auth"])

TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


# ── Request / response models ─────────────────────────────────────────────────

class StudentRegisterRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-z0-9_]+$")
    pin: str = Field(..., min_length=4, max_length=4, pattern=r"^[0-9]{4}$")
    grade_level: str = Field(default="K-2")


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


class StudentAuthResponse(BaseModel):
    token: str
    student_id: str
    user: StudentUserOut


# ── Helpers ────────────────────────────────────────────────────────────────────

def mint_student_token(user_id: str) -> str:
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="Server misconfiguration: SUPABASE_JWT_SECRET not set.")
    now = int(time.time())
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "app_metadata": {"role": "STUDENT"},
    }
    return jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")


async def load_student_user(conn: asyncpg.Connection, user_id: str) -> StudentUserOut | None:
    row = await conn.fetchrow(
        """
        SELECT u.id, u.name, u.username, u.xp, u."adeCoins", u."avatarData",
               u."gradeLevel", u."linkCode", u."parentId", p.name AS parent_name
        FROM "User" u
        LEFT JOIN "User" p ON p.id = u."parentId"
        WHERE u.id = $1
        """,
        user_id,
    )
    if not row:
        return None
    return StudentUserOut(
        id=row["id"],
        display_name=row["name"],
        username=row["username"] or "",
        xp=row["xp"],
        ade_coins=row["adeCoins"],
        avatar_data=json.loads(row["avatarData"]) if row["avatarData"] else {},
        grade_level=row["gradeLevel"] or "K-2",
        link_code=row["linkCode"] or "",
        parent_id=row["parentId"],
        parent_display_name=row["parent_name"],
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
async def register_student_account(body: StudentRegisterRequest):
    user_id = str(uuid.uuid4())
    link_code = user_id.replace("-", "")[:6].upper()
    pin_hash = bcrypt.hashpw(body.pin.encode(), bcrypt.gensalt()).decode()
    placeholder_email = f"{body.username}@mobile.adelineworld.local"

    conn = await get_db_conn()
    try:
        # Ensure table exists (outside transaction, idempotent DDL)
        await conn.execute(
            """
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
        )

        # Both INSERTs in a transaction for atomicity
        async with conn.transaction():
            try:
                await conn.execute(
                    """
                    INSERT INTO "User"
                        (id, name, email, role, "isHomestead", "gradeLevel",
                         username, "pinHash", "linkCode", xp, "adeCoins")
                    VALUES ($1, $2, $3, 'STUDENT', TRUE, $4, $5, $6, $7, 0, 0)
                    """,
                    user_id, body.display_name, placeholder_email, body.grade_level,
                    body.username, pin_hash, link_code,
                )
            except asyncpg.UniqueViolationError:
                raise HTTPException(status_code=409, detail="That username is already taken.")
            except asyncpg.PostgresError as e:
                logger.exception("Database error during student registration")
                raise HTTPException(status_code=500, detail="Registration failed.")

            await _ensure_student_profiles_row(conn, user_id, body.display_name, body.grade_level)

        user = await load_student_user(conn, user_id)
    finally:
        await conn.close()

    if not user:
        raise HTTPException(status_code=500, detail="Registration failed.")
    token = mint_student_token(user_id)
    return StudentAuthResponse(token=token, student_id=user_id, user=user)


@router.post("/login", response_model=StudentAuthResponse)
async def login_student(body: StudentLoginRequest):
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            """SELECT id, "pinHash" FROM "User" WHERE username = $1 AND role = 'STUDENT'""",
            body.username,
        )
        if not row or not row["pinHash"] or not bcrypt.checkpw(body.pin.encode(), row["pinHash"].encode()):
            raise HTTPException(status_code=401, detail="Username or PIN is incorrect.")

        user = await load_student_user(conn, row["id"])
    finally:
        await conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Username or PIN is incorrect.")
    token = mint_student_token(row["id"])
    return StudentAuthResponse(token=token, student_id=row["id"], user=user)
