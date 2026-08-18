"""Life activities should be recognized for learning before clock time."""

from app.api.activities import (
    ActivityReportRequest,
    CreditedTrack,
    _build_learning_note,
    _calc_credit_hours,
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
