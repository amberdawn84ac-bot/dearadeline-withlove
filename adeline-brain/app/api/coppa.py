"""
COPPA Token API — /api/coppa

Internal endpoints called by the Next.js API route, not directly by clients.

POST /api/coppa/token   — store a pending verification token for a student
POST /api/coppa/verify  — validate token, mark coppaVerified = true
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from app.api.middleware import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/coppa", tags=["coppa"])


async def _get_conn():
    from app.config import get_db_conn
    return await get_db_conn()


# ── Pydantic models ───────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    studentId: str
    token: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]+$")
    expiresAt: str  # ISO-8601


class VerifyRequest(BaseModel):
    token: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]+$")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/token", status_code=200)
async def store_token(
    request: TokenRequest,
    authorization: Optional[str] = Header(None),
):
    """Store a COPPA verification token. Called by the Next.js /api/coppa route."""
    authenticated_user_id = get_current_user_id(authorization=authorization)
    if authenticated_user_id != request.studentId:
        raise HTTPException(status_code=403, detail="Cannot create consent for another learner")
    conn = await _get_conn()
    try:
        expires = datetime.fromisoformat(request.expiresAt.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if expires <= now or expires > now + timedelta(hours=73):
            raise HTTPException(status_code=422, detail="Consent link expiry must be within 73 hours")
        token_hash = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
        row = await conn.fetchrow(
            """
            UPDATE "User"
            SET "coppaPendingToken" = $2,
                "coppaTokenExpiresAt" = $3,
                "updatedAt" = NOW()
            WHERE "id" = $1 AND role = 'STUDENT' AND "coppaVerified" = false
            RETURNING "id"
            """,
            request.studentId, token_hash, expires,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Student not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[POST /api/coppa/token] DB error")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

    logger.info(f"[COPPA] Token stored for student {request.studentId}")
    return {"ok": True}


@router.post("/verify", status_code=200)
async def verify_token(request: VerifyRequest):
    """Parent clicks verification link. Validates token, sets coppaVerified = true."""
    conn = await _get_conn()
    try:
        token_hash = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
        row = await conn.fetchrow(
            """
            SELECT "id", "parentEmail", "coppaTokenExpiresAt", "coppaVerified"
            FROM "User"
            WHERE "coppaPendingToken" = $1 OR "coppaPendingToken" = $2
            """,
            token_hash, request.token,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Token not found or already used")

        if row["coppaVerified"]:
            # Already verified — idempotent success
            return {"ok": True, "studentId": str(row["id"])}

        expires = row["coppaTokenExpiresAt"]
        if expires and expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Verification link has expired")

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE "User"
                SET "coppaVerified" = true,
                    "coppaPendingToken" = NULL,
                    "coppaTokenExpiresAt" = NULL,
                    "updatedAt" = NOW()
                WHERE "id" = $1
                """,
                row["id"],
            )
            await conn.execute(
                '''INSERT INTO "ChildPrivacyConsent"
                     ("studentId", "parentEmail", method, "privacyNoticeVersion", "consentedAt")
                   VALUES ($1, $2, 'verified_parent_email', '2026-08-23', NOW())''',
                str(row["id"]), str(row["parentEmail"] or "").lower(),
            )
        logger.info(f"[COPPA] Student {row['id']} verified by parent")
        return {"ok": True, "studentId": str(row["id"])}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[POST /api/coppa/verify] DB error")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()
