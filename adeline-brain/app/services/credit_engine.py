"""
Credit accumulation engine — pure functions for standards/credit/evidence ledger logic.
No database calls — all state passed in, results passed out.
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from datetime import datetime


class ArtifactType(str, Enum):
    ESSAY = "essay"
    QUIZ = "quiz"
    LAB = "lab"
    PROJECT = "project"
    DISCUSSION = "discussion"
    FIELDWORK = "fieldwork"
    PRESENTATION = "presentation"


@dataclass
class Evidence:
    artifact_type: ArtifactType
    mastery_score: float
    hours: float
    activity_date: datetime


@dataclass
class CreditHourWeighting:
    essay: float
    quiz: float
    lab: float
    project: float
    discussion: float
    fieldwork: float
    presentation: float

    def get_weight(self, artifact_type: ArtifactType) -> float:
        return getattr(self, artifact_type.value)


@dataclass
class CreditBucketAccumulation:
    bucket_name: str
    hours_earned: float = 0.0
    evidence_count: int = 0
    mastery_average: float = 0.0


@dataclass
class CourseProposal:
    bucket: str
    external_course_name: str
    hours_earned: float
    mastery_percentage: float
    is_approved: bool = False
    proposed_at: Optional[datetime] = None


def calculate_weighted_hours(evidence: Evidence, weighting: CreditHourWeighting) -> float:
    artifact_weight = weighting.get_weight(evidence.artifact_type)
    mastery_factor = 0.5 + (evidence.mastery_score * 0.5)
    return evidence.hours * artifact_weight * mastery_factor


def accumulate_evidence_in_bucket(
    bucket: CreditBucketAccumulation,
    evidence: Evidence,
    weighting: CreditHourWeighting,
) -> CreditBucketAccumulation:
    weighted_hours = calculate_weighted_hours(evidence, weighting)
    old_total_mastery = bucket.mastery_average * bucket.evidence_count
    new_evidence_count = bucket.evidence_count + 1
    bucket.mastery_average = (old_total_mastery + evidence.mastery_score) / new_evidence_count
    bucket.hours_earned += weighted_hours
    bucket.evidence_count = new_evidence_count
    return bucket


def check_credit_threshold(
    bucket: CreditBucketAccumulation,
    full_credit_hours: float = 120.0,
    half_credit_hours: float = 60.0,
) -> Optional[float]:
    if bucket.hours_earned >= full_credit_hours:
        return 1.0
    elif bucket.hours_earned >= half_credit_hours:
        return 0.5
    return None


def propose_course(
    bucket_name: str,
    external_course_name: str,
    hours_earned: float,
    mastery_average: float,
) -> CourseProposal:
    return CourseProposal(
        bucket=bucket_name,
        external_course_name=external_course_name,
        hours_earned=hours_earned,
        mastery_percentage=mastery_average * 100,
        is_approved=False,
        proposed_at=datetime.utcnow(),
    )


def apply_profile_weighting(profile_key: str, profile_data: dict) -> CreditHourWeighting:
    try:
        weights = profile_data["creditHourWeighting"]
        return CreditHourWeighting(
            essay=weights["essay"],
            quiz=weights["quiz"],
            lab=weights["lab"],
            project=weights["project"],
            discussion=weights["discussion"],
            fieldwork=weights["fieldwork"],
            presentation=weights["presentation"],
        )
    except (KeyError, TypeError) as e:
        raise ValueError(f"Profile '{profile_key}' has malformed creditHourWeighting: {e}") from e


def compute_bucket_accumulation(
    bucket_name: str,
    evidence_list: list[Evidence],
    weighting: CreditHourWeighting,
) -> CreditBucketAccumulation:
    bucket = CreditBucketAccumulation(bucket_name=bucket_name)
    for evidence in evidence_list:
        bucket = accumulate_evidence_in_bucket(bucket, evidence, weighting)
    return bucket


def mastery_score_to_grade_letter(mastery: float) -> str:
    if mastery >= 0.93:
        return "A"
    elif mastery >= 0.90:
        return "A-"
    elif mastery >= 0.87:
        return "B+"
    elif mastery >= 0.83:
        return "B"
    elif mastery >= 0.80:
        return "B-"
    elif mastery >= 0.77:
        return "C+"
    elif mastery >= 0.73:
        return "C"
    elif mastery >= 0.70:
        return "C-"
    elif mastery >= 0.60:
        return "D"
    else:
        return "F"
