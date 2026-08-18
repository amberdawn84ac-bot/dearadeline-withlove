"""Life activities should be recognized for learning before clock time."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.activities import (
    ActivityReportRequest,
    BreadLessonCompletionRequest,
    CreditedTrack,
    _bread_standards_for_grade,
    _build_learning_note,
    _calc_credit_hours,
    _map_activity_locally,
    _score_bread_review,
    complete_kitchen_chemistry_bread,
)


def test_activity_time_is_optional():
    report = ActivityReportRequest(
        student_id="student-1",
        grade_level="8",
        description="I baked bread and watched the dough rise.",
    )

    assert report.time_minutes is None


def test_unspecified_time_does_not_invent_credit_hours():
    assert _calc_credit_hours(0) == 0.0


def test_learning_note_centers_bread_science_and_reflection():
    note = _build_learning_note(
        "Observed yeast fermentation and adjusted ingredient ratios.",
        [
            CreditedTrack(
                track="CREATION_SCIENCE",
                subjects=[
                    "Chemistry: Thermodynamics & Fermentation",
                    "Math: Ratios & Measurement",
                ],
                credit_type="CORE",
            )
        ],
    )

    assert note.startswith("That is real learning.")
    assert "Fermentation" in note
    assert "Ratios & Measurement" in note
    assert "What did you notice" in note
    assert "minutes" not in note


def test_bread_maps_without_an_llm_or_duration():
    mapped = _map_activity_locally("I baked bread and watched the dough rise.")

    assert mapped is not None
    assert mapped["categories"][0] == "baking"
    assert mapped["course_title"] == "Applied Chemistry: Bread Fermentation"
    assert mapped["primary_track"] == "CREATION_SCIENCE"
    assert "fermentation" in mapped["activity_description"].lower()


def test_unknown_activity_has_safe_reflection_fallback():
    mapped = _map_activity_locally("I completed something meaningful.", allow_generic=True)

    assert mapped is not None
    assert mapped["course_title"] == "Independent Study"
    assert mapped["primary_track"] == "DISCIPLESHIP"


def test_activity_date_is_parsed_for_asyncpg_instead_of_left_as_string():
    report = ActivityReportRequest(
        student_id="student-1",
        grade_level="8",
        description="I baked bread and watched the dough rise.",
        activity_date="2026-08-18",
    )

    assert report.activity_date is not None
    assert report.activity_date.isoformat() == "2026-08-18"


def test_bread_review_is_scored_on_the_server():
    correct, total = _score_bread_review({
        "yeast": "living_fungus",
        "gas": "carbon_dioxide",
        "gluten": "traps_gas",
        "temperature": "warm_speeds_yeast",
        "oven": "sets_structure_and_browns",
        "ratio": "proportional_scaling",
    })

    assert (correct, total) == (6, 6)


def test_bread_review_rejects_incorrect_concepts():
    correct, total = _score_bread_review({"yeast": "chemical_powder"})

    assert correct == 0
    assert total == 6


def test_bread_standards_are_selected_for_the_learners_grade_band():
    assert "SCIENC_G3_CCC.3.3-5.3" in _bread_standards_for_grade("3")
    assert "SCIENC_G7_7.PS1.2" in _bread_standards_for_grade("8th")
    assert "SCIENC_G9_B.LS2.3" in _bread_standards_for_grade("11")


@pytest.mark.asyncio
async def test_verified_bread_review_creates_portfolio_record(monkeypatch):
    seal_transcript = AsyncMock(return_value=True)
    seal_journal = AsyncMock()
    monkeypatch.setattr("app.api.activities._seal_activity_transcript", seal_transcript)
    monkeypatch.setattr("app.api.activities.journal_store.seal", seal_journal)

    response = await complete_kitchen_chemistry_bread(
        BreadLessonCompletionRequest(
            grade_level="8",
            answers={
                "yeast": "living_fungus",
                "gas": "carbon_dioxide",
                "gluten": "traps_gas",
                "temperature": "warm_speeds_yeast",
                "oven": "sets_structure_and_browns",
                "ratio": "proportional_scaling",
            },
            observations="The dough doubled and showed bubbles beneath the surface.",
            next_test="Compare a cooler proof with a warmer proof.",
        ),
        student_id="student-1",
    )

    assert response.sealed is True
    assert response.score_percent == 100.0
    assert response.course_title == "Kitchen Chemistry: Bread"
    assert response.activity_id.startswith("activity-kitchen-chemistry-bread-")
    assert response.credit_hours == 0.05
    seal_transcript.assert_awaited_once()


@pytest.mark.asyncio
async def test_unverified_bread_review_does_not_create_record(monkeypatch):
    seal_transcript = AsyncMock(return_value=True)
    monkeypatch.setattr("app.api.activities._seal_activity_transcript", seal_transcript)

    with pytest.raises(HTTPException) as exc_info:
        await complete_kitchen_chemistry_bread(
            BreadLessonCompletionRequest(
                grade_level="8",
                answers={"yeast": "chemical_powder"},
                observations="The dough rose and made bubbles across the surface.",
                next_test="I would compare a warm bowl and a cool bowl.",
            ),
            student_id="student-1",
        )

    assert exc_info.value.status_code == 422
    seal_transcript.assert_not_awaited()
