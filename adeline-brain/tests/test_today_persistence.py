"""Instrumentation for the durable Today plan."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Response

from app.api.learning_plan import get_saved_today_plan, pop_completed_lesson


def _saved_plan() -> dict:
    return {
        "plan_version": 8,
        "student_id": "student-1",
        "suggestions": [{
            "id": "today-1", "title": "Creek evidence", "track": "CREATION_SCIENCE",
            "description": "Compare the records.", "emoji": "🔬", "priority": 1.0,
            "source": "zpd", "mission_kind": "learning_mission", "success_criteria": [],
        }],
        "family_investigation": None,
        "individual_skills": [],
        "projects": [],
        "recommended_books": [],
        "total_tracks_active": 1,
        "strongest_track": None,
        "weakest_track": "CREATION_SCIENCE",
        "total_credits_earned": 0,
        "credits_this_week": 0,
        "graduation_progress": {
            "total_required": 23, "total_earned": 0, "percentage_complete": 0,
            "credits_remaining": 23, "on_track": True, "is_high_school": False,
        },
        "credit_gaps": [],
        "grade_standards": [],
        "roadmap": {
            "school_days_per_week": 4, "total_weeks": 36,
            "starts_on": "2026-08-23", "ends_on": "2027-05-01", "months": [],
            "adaptive": True,
        },
        "placement": {
            "declared_level": "8", "working_grade": "8", "placement_required": False,
            "subject_levels": {},
        },
        "coverage": {
            "total_required": 0, "mastered": 0, "remaining": 0, "scheduled": 0,
            "all_required_accounted_for": True, "subjects": [],
        },
        "family_context": {
            "household_id": "family-1", "shared_with_siblings": False, "sibling_count": 0,
        },
        "generated_at": "2026-08-23T12:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_reopening_today_reads_saved_plan_with_zero_planner_calls():
    saved = AsyncMock(return_value=_saved_plan())
    planner = AsyncMock()
    zpd = AsyncMock()
    with (
        patch("app.api.learning_plan.daily_plan_store.get", new=saved),
        patch("app.api.learning_plan.personalized_curriculum_planner", new=planner),
        patch("app.api.learning_plan.tool_get_zpd_candidates", new=zpd),
    ):
        first = await get_saved_today_plan("student-1", Response(), _user_id="student-1")
        second = await get_saved_today_plan("student-1", Response(), _user_id="student-1")

    assert first.model_dump() == second.model_dump()
    assert saved.await_count == 2
    planner.assert_not_awaited()
    zpd.assert_not_awaited()


@pytest.mark.asyncio
async def test_completion_removes_card_without_deleting_today():
    delete_cache = AsyncMock()
    remove_suggestion = AsyncMock(return_value=_saved_plan())
    invalidate = AsyncMock()
    with (
        patch("app.api.learning_plan.redis_client.delete", new=delete_cache),
        patch("app.api.learning_plan.daily_plan_store.remove_suggestion", new=remove_suggestion),
        patch("app.api.learning_plan.daily_plan_store.invalidate", new=invalidate),
    ):
        await pop_completed_lesson("student-1", "Creek evidence")

    delete_cache.assert_awaited_once()
    remove_suggestion.assert_awaited_once()
    invalidate.assert_not_awaited()
