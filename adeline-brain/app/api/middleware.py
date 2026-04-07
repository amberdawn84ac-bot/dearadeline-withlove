"""
Authentication middleware for adeline-brain.

Verifies Supabase JWTs using either:
  1. JWKS (ES256) — fetches public key from Supabase's well-known endpoint
  2. Shared secret (HS256) — uses SUPABASE_JWT_SECRET env var

The token's 'kid' header determines the path. User access tokens from
Supabase Auth v2 use ES256 with a kid; legacy tokens use HS256.

Every request must send: Authorization: Bearer <supabase_access_token>
"""
import logging
from typing import Optional

import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException, Depends
from app.schemas.api_models import UserRole
from app.config import SUPABASE_JWT_SECRET, SUPABASE_JWKS_URL

logger = logging.getLogger(__name__)

_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    """Lazy-init the JWKS client so import doesn't block on network."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(SUPABASE_JWKS_URL, cache_keys=True, lifespan=3600)
    return _jwks_client


def _decode_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase-issued JWT.
    Uses JWKS (ES256) if token has a 'kid' header, otherwise falls back
    to SUPABASE_JWT_SECRET (HS256).
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError as e:
        raise HTTPException(status_code=401, detail=f"Malformed token: {e}")

    kid = header.get("kid")
    alg = header.get("alg", "HS256")

    try:
        if kid:
            # ES256 path — verify with JWKS public key
            client = _get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
            )
        elif SUPABASE_JWT_SECRET:
            # HS256 path — verify with shared secret
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: no JWKS kid and no JWT secret.",
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        logger.error(f"[Auth] JWT verification error: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed.")


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
