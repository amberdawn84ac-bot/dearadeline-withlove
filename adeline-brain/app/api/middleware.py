"""
Authentication helpers for adeline-brain.

Supports both Supabase access tokens and Dear Adeline student JWTs. Browser
clients may authenticate with an Authorization header or the HttpOnly
``auth_token`` cookie issued by the production UI.
"""
import logging
from typing import Optional

import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException, Cookie
from app.schemas.api_models import UserRole
from app.config import STUDENT_JWT_SECRET, SUPABASE_JWKS_URL

logger = logging.getLogger(__name__)

_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    """Lazy-init the JWKS client so import doesn't block on network."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(SUPABASE_JWKS_URL, cache_keys=True, lifespan=3600)
    return _jwks_client


def _decode_jwt(token: str) -> dict:
    """Decode and verify a Supabase or Dear Adeline student JWT."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError as e:
        raise HTTPException(status_code=401, detail=f"Malformed token: {e}")

    kid = header.get("kid")
    alg = header.get("alg", "HS256")

    try:
        if kid:
            client = _get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
            )
        if STUDENT_JWT_SECRET:
            return jwt.decode(
                token,
                STUDENT_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: no student JWT secret.",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Auth] JWT verification error: %s", e)
        raise HTTPException(status_code=401, detail="Token verification failed.")


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
        )
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token.")
    return token


def _token_from_sources(
    authorization: Optional[str],
    auth_token: Optional[str],
) -> str:
    """Prefer Bearer auth, with secure-cookie fallback for browser requests."""
    if authorization:
        try:
            return _extract_bearer_token(authorization)
        except HTTPException:
            pass
    if auth_token:
        return auth_token
    raise HTTPException(status_code=401, detail="Authentication required.")


def _extract_role(payload: dict) -> str:
    app_metadata = payload.get("app_metadata", {})
    return app_metadata.get("role", "STUDENT").upper()


def _extract_user_id(payload: dict) -> str:
    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim.")
    return user_id


def require_role(*allowed_roles: UserRole):
    """FastAPI dependency factory enforcing one of the supplied roles."""
    def _check(
        authorization: Optional[str] = Header(default=None),
        auth_token: Optional[str] = Cookie(default=None),
    ) -> str:
        token = _token_from_sources(authorization, auth_token)
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
    auth_token: Optional[str] = Cookie(default=None),
) -> str:
    """Return the authenticated user id from Bearer header or auth cookie."""
    token = _token_from_sources(authorization, auth_token)
    payload = _decode_jwt(token)
    return _extract_user_id(payload)


def get_current_user_id_from_auth_or_cookie(
    authorization: Optional[str] = Header(default=None),
    auth_token: Optional[str] = Cookie(default=None),
) -> str:
    """Backward-compatible alias for cookie-aware authentication."""
    return get_current_user_id(authorization=authorization, auth_token=auth_token)


def get_auth_claims(authorization: Optional[str]) -> tuple[str, str]:
    token = _extract_bearer_token(authorization)
    payload = _decode_jwt(token)
    user_id = _extract_user_id(payload)
    email = payload.get("email", "")
    return user_id, email


async def verify_student_access(
    student_id: str,
    authorization: Optional[str] = Header(default=None),
    auth_token: Optional[str] = Cookie(default=None),
) -> str:
    """Verify student, parent, or admin access to a student's data."""
    token = _token_from_sources(authorization, auth_token)
    payload = _decode_jwt(token)
    user_id = _extract_user_id(payload)
    role_str = _extract_role(payload)

    return await verify_student_access_for_user(user_id, student_id, token_role=role_str)


async def verify_student_access_for_user(
    user_id: str,
    student_id: str,
    *,
    token_role: str | None = None,
) -> str:
    """Enforce tenant ownership when a route already resolved the caller identity."""
    from app.config import get_db_conn

    conn = await get_db_conn()
    try:
        # Authorization follows the durable account record, not a potentially
        # stale role claim carried by a long-lived browser token.
        stored_role = await conn.fetchval('SELECT role FROM "User" WHERE id = $1', user_id)
        role_str = str(stored_role or "").upper()

        if user_id == student_id and role_str == UserRole.STUDENT.value:
            return user_id
        if role_str == UserRole.ADMIN.value:
            return user_id
        if role_str == UserRole.PARENT.value:
            owns_student = await conn.fetchval(
                'SELECT EXISTS(SELECT 1 FROM "User" WHERE id = $1 AND "parentId" = $2 AND role = \'STUDENT\')',
                student_id,
                user_id,
            )
            if owns_student:
                return user_id
    finally:
        await conn.close()

    raise HTTPException(status_code=403, detail="You do not have access to this student's data.")


def require_account_role(*allowed_roles: UserRole):
    """Authorize using the verified token identity and the durable User role."""
    async def _check(
        authorization: Optional[str] = Header(default=None),
        auth_token: Optional[str] = Cookie(default=None),
    ) -> str:
        token = _token_from_sources(authorization, auth_token)
        user_id = _extract_user_id(_decode_jwt(token))
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            stored_role = await conn.fetchval('SELECT role FROM "User" WHERE id = $1', user_id)
        finally:
            await conn.close()
        role = str(stored_role or "").upper()
        allowed = {item.value for item in allowed_roles}
        if role not in allowed:
            raise HTTPException(status_code=403, detail=f"Access denied. Required account role: {sorted(allowed)}")
        return role
    return _check


def require_internal_key(
    x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key"),
) -> str:
    from app.config import INTERNAL_API_KEY
    if not x_internal_key or x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing internal API key.",
        )
    return x_internal_key
