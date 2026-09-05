from app.api.journal import SealRequest, _concept_credits_from_seal
from app.schemas.api_models import Track


def test_quiz_without_exact_concept_never_guesses_a_mastery_target():
    body = SealRequest(
        lesson_id="lesson-1",
        track=Track.APPLIED_MATHEMATICS,
        quiz_results=[{"correct": True}],
    )
    assert _concept_credits_from_seal(body) == []


def test_quiz_updates_only_the_exact_planned_concept():
    body = SealRequest(
        lesson_id="lesson-1",
        track=Track.APPLIED_MATHEMATICS,
        concept_id="am-003",
        concept_name="Fractions in Real Life",
        quiz_results=[{"correct": True}],
    )
    credits = _concept_credits_from_seal(body)
    assert len(credits) == 1
    assert credits[0].concept_id == "am-003"
    assert credits[0].concept_name == "Fractions in Real Life"
