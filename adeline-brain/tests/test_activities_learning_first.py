"""Life activities should be recognized for learning before clock time."""

from app.api.activities import (
    ActivityReportRequest,
    CreditedTrack,
    _build_learning_note,
    _calc_credit_hours,
    _map_activity_locally,
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
