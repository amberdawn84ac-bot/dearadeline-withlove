"""Inspectable contracts for the learning-agent team."""
from fastapi import APIRouter

router = APIRouter(prefix="/agent-team", tags=["agent-team"])


@router.get("/status")
async def agent_team_status():
    """Expose ownership and handoffs without exposing prompts or private learner data."""
    return {
        "status": "ready",
        "agents": [
            {"name": "MissionArchitect", "owns": "mission selection and finish line", "hands_off_to": "CurriculumLibrarian"},
            {"name": "CurriculumLibrarian", "owns": "canonical lookup before generation", "hands_off_to": "subject specialist"},
            {"name": "Historian", "owns": ["TRUTH_HISTORY"]},
            {"name": "Justice", "owns": ["JUSTICE_CHANGEMAKING"]},
            {"name": "Science", "owns": ["CREATION_SCIENCE", "HEALTH_NATUROPATHY", "HOMESTEADING"]},
            {"name": "Literature", "owns": ["ENGLISH_LITERATURE"]},
            {"name": "Practical", "owns": ["APPLIED_MATHEMATICS", "GOVERNMENT_ECONOMICS", "CREATIVE_ECONOMY"]},
            {"name": "Discipleship", "owns": ["DISCIPLESHIP"]},
            {"name": "GameSmith", "owns": "canonical-grounded 2D game contract", "hands_off_to": "Game Portal runtime"},
            {"name": "PortfolioCurator", "owns": "learner-facing portfolio invitation", "hands_off_to": "portfolio and standards storage"},
            {"name": "Registrar", "owns": "alignment draft and completion-sealed credit", "awards_on_generation": False},
        ],
    }
