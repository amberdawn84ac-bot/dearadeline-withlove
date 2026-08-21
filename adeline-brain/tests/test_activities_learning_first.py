"""Life activities earn credit for demonstrated concepts, never clock time."""

from app.api.activities import (
    ActivityReportRequest,
    CreditedTrack,
    _build_learning_note,
    _competency_credit,
    _map_activity_locally,
)


def test_activity_time_is_optional():
    report = ActivityReportRequest(
        student_id="student-1",
        grade_level="8",
        description="I baked bread and watched the dough rise.",
    )

    assert report.time_minutes is None


def test_credit_is_proportional_to_mastered_requirements_not_time():
    standards = [
        {"id": "SCI.1", "subject": "Science"},
        {"id": "SCI.2", "subject": "Science"},
        {"id": "MATH.1", "subject": "Mathematics"},
        {"id": "MATH.2", "subject": "Mathematics"},
        {"id": "MATH.3", "subject": "Mathematics"},
        {"id": "MATH.4", "subject": "Mathematics"},
    ]
    assert _competency_credit([], standards) == 0.0
    assert _competency_credit(["SCI.1"], standards) == 0.5
    assert _competency_credit(["SCI.1", "MATH.1"], standards) == 0.75


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
        ["yeast fermentation", "proportional reasoning"],
        None,
    )

    assert note.startswith("That demonstrates real learning")
    assert "Fermentation" in note
    assert "Ratios & Measurement" in note
    assert "yeast fermentation" in note
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
