"""
Authentication middleware for adeline-brain.

Production (SUPABASE_JWT_SECRET set):
    Verifies the Bearer token from the Authorization header as a Supabase JWT.
    Extracts user_id and role from the token claims.

Development (SUPABASE_JWT_SECRET not set):
    Falls back to header-based auth (X-User-Role + X-User-Id) for local dev.
    Logs a warning on first use so this never silently runs in production.
"""
import logging
from typing import Optional

import jwt
from fastapi import Header, HTTPException
from app.schemas.api_models import UserRole
from app.config import SUPABASE_JWT_SECRET, IS_PRODUCTION

logger = logging.getLogger(__name__)

_dev_warning_logged = False


def _decode_supabase_jwt(token: str) -> dict:
    """Decode and verify a Supabase-issued JWT."""
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


def _extract_role_from_jwt(payload: dict) -> str:
    """Extract the user role from Supabase JWT app_metadata."""
    app_metadata = payload.get("app_metadata", {})
    role = app_metadata.get("role", "STUDENT").upper()
    return role


def _extract_user_id_from_jwt(payload: dict) -> str:
    """Extract the user ID (Supabase sub claim)."""
    return payload.get("sub", "")


def require_role(*allowed_roles: UserRole):
    """
    FastAPI dependency factory. Returns a dependency that enforces
    that the authenticated user has one of the allowed roles.

    In production: verifies Bearer JWT from Authorization header.
    In development: accepts X-User-Role header (with warning).

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """

    def _check(
        authorization: Optional[str] = Header(default=None),
        x_user_role: Optional[str] = Header(default=None),
        x_user_id: Optional[str] = Header(default=None),
    ) -> str:
        global _dev_warning_logged

        # ── Production path: JWT verification ─────────────────────────────
        if SUPABASE_JWT_SECRET:
            if not authorization or not authorization.startswith("Bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="Missing or invalid Authorization header. Expected: Bearer <token>",
                )
            token = authorization[7:]  # Strip "Bearer "
            payload = _decode_supabase_jwt(token)
            role_str = _extract_role_from_jwt(payload)

            try:
                role = UserRole(role_str)
            except ValueError:
                raise HTTPException(status_code=401, detail=f"Unknown role in token: {role_str}")

            if role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Access denied. Required: {[r.value for r in allowed_roles]}. "
                        f"Your role: {role.value}"
                    ),
                )
            return role.value

        # ── Development fallback: header-based auth ───────────────────────
        if IS_PRODUCTION:
            raise HTTPException(
                status_code=500,
                detail="JWT secret not configured. Cannot authenticate in production.",
            )

        if not _dev_warning_logged:
            logger.warning(
                "[Auth] Using development header-based auth (X-User-Role). "
                "Set SUPABASE_JWT_SECRET for production JWT verification."
            )
            _dev_warning_logged = True

        if not x_user_role:
            raise HTTPException(status_code=401, detail="Missing X-User-Role header.")

        try:
            role = UserRole(x_user_role.upper())
        except ValueError:
            raise HTTPException(status_code=401, detail=f"Invalid role: {x_user_role}")

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
