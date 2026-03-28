"""
Opportunities API — /api/opportunities
Local Oklahoma K-12 events and field opportunities.
ADMIN-only: parents and students cannot browse the full list.
"""
from fastapi import APIRouter, Depends
from app.api.middleware import require_role
from app.schemas.api_models import UserRole

router = APIRouter(prefix="/api", tags=["opportunities"])


@router.get(
    "/opportunities",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def list_opportunities():
    """
    Returns curated local Oklahoma learning opportunities.
    Restricted to ADMIN role — curriculum directors manage this list.
    """
    return {
        "opportunities": [
            {
                "id": "opp-001",
                "title": "Oklahoma History Center Field Study",
                "location": "Oklahoma City, OK",
                "track": "TRUTH_HISTORY",
                "grades": ["5", "6", "7", "8"],
                "description": (
                    "Guided primary-source tour of Oklahoma Territory documents, "
                    "land run maps, and Indigenous nation treaties."
                ),
            },
            {
                "id": "opp-002",
                "title": "Kerr Center Sustainable Agriculture Tour",
                "location": "Poteau, OK",
                "track": "HOMESTEADING",
                "grades": ["3", "4", "5", "6"],
                "description": (
                    "Hands-on homestead science — soil health, seed saving, "
                    "and water stewardship on a working regenerative farm."
                ),
            },
        ],
        "total": 2,
        "admin_note": "Only ADMIN users can view and manage this list.",
    }
