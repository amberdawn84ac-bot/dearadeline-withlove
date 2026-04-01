import pytest
from datetime import datetime
from app.services.credit_engine import (
    Evidence, ArtifactType, CreditHourWeighting, CreditBucketAccumulation,
    calculate_weighted_hours, accumulate_evidence_in_bucket,
    check_credit_threshold, propose_course, apply_profile_weighting,
    compute_bucket_accumulation, mastery_score_to_grade_letter,
)


@pytest.fixture
def sample_weighting():
    return CreditHourWeighting(
        essay=1.0, quiz=0.5, lab=1.5, project=1.75,
        discussion=0.75, fieldwork=1.25, presentation=1.25,
    )


def test_calculate_weighted_hours_perfect_essay(sample_weighting):
    evidence = Evidence(artifact_type=ArtifactType.ESSAY, mastery_score=1.0, hours=10.0, activity_date=datetime.utcnow())
    assert calculate_weighted_hours(evidence, sample_weighting) == 10.0


def test_calculate_weighted_hours_half_mastery_essay(sample_weighting):
    evidence = Evidence(artifact_type=ArtifactType.ESSAY, mastery_score=0.5, hours=10.0, activity_date=datetime.utcnow())
    assert calculate_weighted_hours(evidence, sample_weighting) == 7.5


def test_calculate_weighted_hours_low_mastery_quiz(sample_weighting):
    evidence = Evidence(artifact_type=ArtifactType.QUIZ, mastery_score=0.2, hours=5.0, activity_date=datetime.utcnow())
    assert calculate_weighted_hours(evidence, sample_weighting) == pytest.approx(1.5)


def test_accumulate_evidence_updates_running_average(sample_weighting):
    bucket = CreditBucketAccumulation(bucket_name="ENGLISH")
    e1 = Evidence(artifact_type=ArtifactType.ESSAY, mastery_score=0.8, hours=5.0, activity_date=datetime.utcnow())
    bucket = accumulate_evidence_in_bucket(bucket, e1, sample_weighting)
    assert bucket.evidence_count == 1
    assert bucket.mastery_average == pytest.approx(0.8)
    e2 = Evidence(artifact_type=ArtifactType.ESSAY, mastery_score=0.9, hours=5.0, activity_date=datetime.utcnow())
    bucket = accumulate_evidence_in_bucket(bucket, e2, sample_weighting)
    assert bucket.evidence_count == 2
    assert bucket.mastery_average == pytest.approx(0.85)


def test_check_credit_threshold_full_credit():
    bucket = CreditBucketAccumulation(bucket_name="ENGLISH", hours_earned=125.0, evidence_count=1, mastery_average=0.85)
    assert check_credit_threshold(bucket, full_credit_hours=120.0) == 1.0


def test_check_credit_threshold_half_credit():
    bucket = CreditBucketAccumulation(bucket_name="ENGLISH", hours_earned=80.0, evidence_count=1, mastery_average=0.85)
    assert check_credit_threshold(bucket, full_credit_hours=120.0, half_credit_hours=60.0) == 0.5


def test_check_credit_threshold_none_below_half():
    bucket = CreditBucketAccumulation(bucket_name="ENGLISH", hours_earned=30.0, evidence_count=1, mastery_average=0.85)
    assert check_credit_threshold(bucket, half_credit_hours=60.0) is None


def test_propose_course():
    proposal = propose_course(bucket_name="ENGLISH", external_course_name="English Language Arts", hours_earned=125.0, mastery_average=0.87)
    assert proposal.bucket == "ENGLISH"
    assert proposal.external_course_name == "English Language Arts"
    assert proposal.mastery_percentage == 87.0
    assert proposal.is_approved is False


def test_apply_profile_weighting_success():
    profile = {"creditHourWeighting": {"essay": 1.0, "quiz": 0.5, "lab": 1.5, "project": 1.75, "discussion": 0.75, "fieldwork": 1.25, "presentation": 1.25}}
    weighting = apply_profile_weighting("test", profile)
    assert weighting.essay == 1.0


def test_apply_profile_weighting_malformed():
    with pytest.raises(ValueError):
        apply_profile_weighting("bad", {"creditHourWeighting": None})


def test_compute_bucket_accumulation():
    weighting = CreditHourWeighting(essay=1.0, quiz=0.5, lab=1.5, project=1.75, discussion=0.75, fieldwork=1.25, presentation=1.25)
    evidence = [
        Evidence(artifact_type=ArtifactType.ESSAY, mastery_score=0.85, hours=10.0, activity_date=datetime.utcnow()),
        Evidence(artifact_type=ArtifactType.LAB, mastery_score=0.9, hours=8.0, activity_date=datetime.utcnow()),
    ]
    bucket = compute_bucket_accumulation("ENGLISH", evidence, weighting)
    assert bucket.evidence_count == 2
    assert bucket.hours_earned == pytest.approx(20.65)


def test_mastery_score_to_grade_letter():
    assert mastery_score_to_grade_letter(0.95) == "A"
    assert mastery_score_to_grade_letter(0.87) == "B+"
    assert mastery_score_to_grade_letter(0.80) == "B-"
    assert mastery_score_to_grade_letter(0.70) == "C-"
    assert mastery_score_to_grade_letter(0.60) == "D"
    assert mastery_score_to_grade_letter(0.45) == "F"
