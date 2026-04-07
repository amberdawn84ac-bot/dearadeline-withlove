"""
Authentication middleware for adeline-brain.

All environments use JWT verification via SUPABASE_JWT_SECRET.
The JWT is a Supabase access_token sent as `Authorization: Bearer <token>`.
The 'sub' claim is the user UUID; role comes from app_metadata.role.

There is NO unverified fallback. If the secret is missing, requests are rejected.
"""
import logging
from typing import Optional

import jwt
from fastapi import Header, HTTPException, Depends
from app.schemas.api_models import UserRole
from app.config import SUPABASE_JWT_SECRET

logger = logging.getLogger(__name__)


def _decode_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase-issued JWT.
    Raises HTTPException on any failure.
    """
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: JWT secret not set.",
        )
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def _extract_bearer_token(authorization: Optional[str]) -> str:
    """Extract the raw token from an Authorization: Bearer header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
        )
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token.")
    return token


def _extract_role(payload: dict) -> str:
    """Extract the user role from Supabase JWT app_metadata."""
    app_metadata = payload.get("app_metadata", {})
    return app_metadata.get("role", "STUDENT").upper()


def _extract_user_id(payload: dict) -> str:
    """Extract the user ID (Supabase 'sub' claim)."""
    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim.")
    return user_id


# ── Public dependencies ──────────────────────────────────────────────────────


def require_role(*allowed_roles: UserRole):
    """
    FastAPI dependency factory.
    Verifies the Bearer JWT and checks that the user's role is allowed.

    Returns the role string on success.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """

    def _check(
        authorization: Optional[str] = Header(default=None),
    ) -> str:
        token = _extract_bearer_token(authorization)
        payload = _decode_jwt(token)
        role_str = _extract_role(payload)

        try:
            role = UserRole(role_str)
        except ValueError:
            raise HTTPException(status_code=401, detail=f"Unknown role: {role_str}")

        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Access denied. Required: {[r.value for r in allowed_roles]}. "
                    f"Your role: {role.value}"
                ),
            )
        return role.value

    return _check


def get_current_user_id(
    authorization: Optional[str] = Header(default=None),
) -> str:
    """
    FastAPI dependency.
    Decodes the Bearer JWT and returns the authenticated user's UUID.

    Usage:
        @router.get("/me")
        async def get_me(user_id: str = Depends(get_current_user_id)):
    """
    token = _extract_bearer_token(authorization)
    payload = _decode_jwt(token)
    return _extract_user_id(payload)
