"""
Role-based access middleware for adeline-brain.
Uses a simple header-based guard (X-User-Role + X-User-Id) until full
JWT auth is wired. The dependency is designed to be swapped for a real
token-decode function without changing any route signatures.
"""
from fastapi import Header, HTTPException, Depends
from app.schemas.api_models import UserRole


def require_role(*allowed_roles: UserRole):
    """
    FastAPI dependency factory. Returns a dependency that enforces
    that X-User-Role is one of the allowed_roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    def _check(x_user_role: str = Header(default="")) -> str:
        try:
            role = UserRole(x_user_role.upper())
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid X-User-Role header.",
            )
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Access denied. Required role(s): "
                    f"{[r.value for r in allowed_roles]}. "
                    f"Your role: {role.value}"
                ),
            )
        return role.value
    return _check
