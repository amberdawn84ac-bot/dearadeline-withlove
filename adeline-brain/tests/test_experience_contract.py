from app.api.journal import SealRequest, _evidence_proficiency
from app.curriculum.experience_contract import annotate_experience, validate_experience
from app.schemas.api_models import Track


def test_experience_requires_action_and_demonstration():
    blocks = annotate_experience([
        {"block_type": "TEXT", "content": "Why did the creek change course?"},
        {"block_type": "PRIMARY_SOURCE", "content": "Examine these two maps."},
    ])
    errors = validate_experience(blocks)
    assert any("action or creation" in error for error in errors)
    assert any("demonstration" in error for error in errors)


def test_reflection_records_exposure_not_mastery():
    request = SealRequest(
        lesson_id="lesson-1",
        track=Track.CREATION_SCIENCE,
        learner_reflection="I changed my prediction after the second observation.",
    )
    assert _evidence_proficiency(request) == "DEVELOPING"


def test_scored_demonstration_can_reach_understanding():
    request = SealRequest(
        lesson_id="lesson-1",
        track=Track.CREATION_SCIENCE,
        quiz_results=[{"correct": True}, {"correct": True}, {"correct": True}, {"correct": False}],
    )
    assert _evidence_proficiency(request) == "UNDERSTANDING"


def test_extending_requires_strong_score_plus_real_artifact():
    request = SealRequest(
        lesson_id="lesson-1",
        track=Track.CREATION_SCIENCE,
        quiz_results=[{"correct": True}] * 10,
        artifact_refs=["portfolio://artifact-1"],
    )
    assert _evidence_proficiency(request) == "EXTENDING"
