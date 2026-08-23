"""Regression checks that completion/time cannot masquerade as mastery."""
from app.api.journal import SealRequest, _quiz_quality


def test_unscored_completion_is_not_a_correct_bkt_response():
    assert _quiz_quality([]) == 0
    assert _quiz_quality([{"correct": True}, {"correct": False}]) == 2


def test_learner_cannot_submit_a_transcript_credit_amount():
    request = SealRequest.model_validate({
        "lesson_id": "experience-1",
        "track": "CREATION_SCIENCE",
        "learner_reflection": "I tested the claim and explained what the evidence showed.",
        "credit_draft": {"credit_hours": 99},
    })
    assert not hasattr(request, "credit_draft")
