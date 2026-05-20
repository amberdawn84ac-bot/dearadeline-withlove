"""
Authentication cookie endpoints for production-grade XSS-proof auth.

These endpoints manage HttpOnly, Secure, SameSite cookies containing
Supabase JWT tokens. This eliminates localStorage-based token storage
which is vulnerable to XSS attacks.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Response, Request
from pydantic import BaseModel

from app.api.middleware import get_current_user_id, get_auth_claims

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie settings for production security
COOKIE_NAME = "auth_token"
COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds
COOKIE_PATH = "/brain"  # Cookie only sent to backend routes


class SessionRequest(BaseModel):
    """Request to set auth cookie."""
    token: str


class SessionResponse(BaseModel):
    """Response from session endpoints."""
    ok: bool
    user_id: Optional[str] = None


@router.post("/session", response_model=SessionResponse)
async def set_auth_cookie(
    response: Response,
    request: SessionRequest,
):
    """
    Set HttpOnly auth cookie with Supabase JWT token.
    
    Call this immediately after Supabase login/signup to establish
    the secure cookie session. The cookie is automatically sent
    with all subsequent /brain/* API requests.
    
    Cookie settings:
    - HttpOnly: Prevents JavaScript access (XSS protection)
    - Secure: HTTPS only
    - SameSite=Lax: CSRF protection while allowing top-level navigation
    - Path=/brain: Only sent to backend API routes
    - Max-Age=7 days
    """
    try:
        # Validate the token by extracting user_id
        from app.api.middleware import _extract_bearer_token, _decode_jwt, _extract_user_id
        token = _extract_bearer_token(f"Bearer {request.token}")
        payload = _decode_jwt(token)
        user_id = _extract_user_id(payload)
        
        # Set the HttpOnly cookie
        response.set_cookie(
            key=COOKIE_NAME,
            value=request.token,
            max_age=COOKIE_MAX_AGE,
            path=COOKIE_PATH,
            httponly=True,
            secure=True,
            samesite="lax",
        )
        
        logger.info(f"[Auth] Set auth cookie for user {user_id}")
        return SessionResponse(ok=True, user_id=user_id)
        
    except Exception as e:
        logger.error(f"[Auth] Failed to set auth cookie: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


@router.delete("/session", response_model=SessionResponse)
async def clear_auth_cookie(response: Response):
    """
    Clear the auth cookie (logout).
    
    Call this on logout to immediately invalidate the session.
    """
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
    )
    logger.info("[Auth] Cleared auth cookie")
    return SessionResponse(ok=True)


@router.get("/session", response_model=SessionResponse)
async def get_session_status(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """
    Check if user has valid session (header or cookie).
    
    Returns user_id if authenticated, 401 otherwise.
    Useful for frontend to check session on page load.
    """
    try:
        # Try Authorization header first
        if authorization:
            user_id = get_current_user_id(authorization=authorization)
            return SessionResponse(ok=True, user_id=user_id)
        
        # Fall back to cookie
        cookie_token = request.cookies.get(COOKIE_NAME)
        if cookie_token:
            from app.api.middleware import _decode_jwt, _extract_user_id
            payload = _decode_jwt(cookie_token)
            user_id = _extract_user_id(payload)
            return SessionResponse(ok=True, user_id=user_id)
        
        raise HTTPException(status_code=401, detail="No valid session")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Auth] Session check failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid session")
