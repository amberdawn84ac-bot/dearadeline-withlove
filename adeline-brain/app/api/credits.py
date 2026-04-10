"""
Credits API — /api/credits
Standards accumulation, credit hour tracking, course proposal approval.
"""
import json
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.middleware import verify_student_access
from app.services.credit_engine import (
    ArtifactType,
    CreditBucketAccumulation,
    CourseProposal,
    CreditHourWeighting,
    Evidence,
    apply_profile_weighting,
    calculate_weighted_hours,
    check_credit_threshold,
    compute_bucket_accumulation,
    mastery_score_to_grade_letter,
    propose_course,
)

router = APIRouter(prefix="/api", tags=["credits"])


# Pydantic Models
class EvidenceInput(BaseModel):
    artifact_type: ArtifactType
    mastery_score: float = Field(ge=0.0, le=1.0)
    hours: float = Field(gt=0.0)


class CreditBucketResponse(BaseModel):
    bucket_name: str
    hours_earned: float
    evidence_count: int
    mastery_average: float
    credit_earned: Optional[float] = None


class CourseProposalResponse(BaseModel):
    proposal_id: str
    bucket: str
    external_course_name: str
    hours_earned: float
    mastery_percentage: float
    is_approved: bool


class ProfileResponse(BaseModel):
    profile_key: str
    name: str
    description: str
    oasOptional: bool
    creditHourWeighting: dict


class CreditDashboardResponse(BaseModel):
    student_id: str
    selected_profile: str
    buckets: list[CreditBucketResponse]
    pending_proposals: list[CourseProposalResponse]


# Helper Functions
def load_oklahoma_profiles() -> dict:
    """Load Oklahoma education profiles from JSON file."""
    profile_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "oklahoma_profiles.json"
    )
    with open(profile_path, "r") as f:
        return json.load(f)


# Endpoints
@router.get("/credits/available-profiles")
async def list_available_profiles() -> dict:
    """
    Returns all available Oklahoma education profiles.
    """
    profiles = load_oklahoma_profiles()
    profile_responses = [
        ProfileResponse(
            profile_key=key,
            name=data.get("name", ""),
            description=data.get("description", ""),
            oasOptional=data.get("oasOptional", False),
            creditHourWeighting=data.get("creditHourWeighting", {}),
        )
        for key, data in profiles.items()
    ]
    return {"profiles": profile_responses}


@router.get("/credits/{student_id}/profile")
async def get_student_profile(student_id: str, _user_id: str = Depends(verify_student_access)) -> dict:
    """
    Returns the current credit profile selection for a student.
    In production, this would fetch from the database.
    """
    return {
        "student_id": student_id,
        "selected_profile": "oklahoma_flexible_homeschool",
        "message": "Placeholder — would fetch from database in production",
    }


@router.put("/credits/{student_id}/profile")
async def set_student_profile(student_id: str, profile_key: str, _user_id: str = Depends(verify_student_access)) -> dict:
    """
    Sets the student's credit profile.
    In production, this would persist to the database.
    """
    profiles = load_oklahoma_profiles()
    if profile_key not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "student_id": student_id,
        "selected_profile": profile_key,
        "message": f"Profile set to {profiles[profile_key]['name']}",
    }


@router.get("/credits/{student_id}")
async def get_credit_dashboard(student_id: str, _user_id: str = Depends(verify_student_access)) -> CreditDashboardResponse:
    """
    Returns the credit dashboard for a student — accumulated hours,
    pending proposals, and thresholds.
    In production, this would fetch evidence from the database.
    """
    return CreditDashboardResponse(
        student_id=student_id,
        selected_profile="oklahoma_flexible_homeschool",
        buckets=[],
        pending_proposals=[],
    )


@router.post("/credits/{student_id}/approve/{proposal_id}")
async def approve_course_proposal(
    student_id: str, proposal_id: str, _user_id: str = Depends(verify_student_access)
) -> dict:
    """
    Approves a course proposal and adds it to the student's transcript.
    In production, this would update the database and emit xAPI/CASE records.
    """
    return {
        "student_id": student_id,
        "proposal_id": proposal_id,
        "is_approved": True,
        "message": "Course proposal approved",
    }
