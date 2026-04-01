"""
Post-lesson credit accumulation hook.
Called after RegistrarAgent seals a lesson.
Records standards, accumulates credit hours, proposes courses.
"""
from datetime import datetime
from typing import Any
from pathlib import Path
import json

from app.services.credit_engine import (
    apply_profile_weighting,
    check_credit_threshold,
    CreditBucketAccumulation,
    ArtifactType,
)
from app.services.standards_mapper import map_lesson_to_oas


def _load_profiles() -> dict:
    profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
    with open(profiles_path) as f:
        return json.load(f)


# Track → primary credit bucket mapping (mirrors adeline-core config/tracks.ts)
TRACK_BUCKET_MAP = {
    "CREATION_SCIENCE": "LAB_SCIENCE",
    "HEALTH_NATUROPATHY": "HEALTH",
    "HOMESTEADING": "LAB_SCIENCE",
    "GOVERNMENT_ECONOMICS": "SOCIAL_STUDIES",
    "JUSTICE_CHANGEMAKING": "SOCIAL_STUDIES",
    "DISCIPLESHIP": "ELECTIVE",
    "TRUTH_HISTORY": "SOCIAL_STUDIES",
    "ENGLISH_LITERATURE": "ENGLISH",
    "APPLIED_MATHEMATICS": "MATH",
    "CREATIVE_ECONOMY": "FINE_ARTS",
}

TRACK_EXTERNAL_NAME = {
    "CREATION_SCIENCE": "Environmental Science",
    "HEALTH_NATUROPATHY": "Health Science",
    "HOMESTEADING": "Agricultural Science & Technology",
    "GOVERNMENT_ECONOMICS": "Government & Economics",
    "JUSTICE_CHANGEMAKING": "Social Studies & Civics",
    "DISCIPLESHIP": "Philosophy & Ethics",
    "TRUTH_HISTORY": "American & World History",
    "ENGLISH_LITERATURE": "English Language Arts",
    "APPLIED_MATHEMATICS": "Applied Mathematics",
    "CREATIVE_ECONOMY": "Art, Design & Entrepreneurship",
}


async def accumulate_credit_from_lesson(
    student_id: str,
    lesson_id: str,
    track: str,
    lesson_title: str,
    estimated_minutes: int,
    mastery_score: float,
    activity_date: datetime,
    prisma: Any,
) -> None:
    """
    Called after RegistrarAgent seals a lesson.

    1. Records OAS standards addressed (StandardsLedgerEntry)
    2. Records evidence artifact (EvidenceLedgerEntry)
    3. Accumulates credit hours (CreditLedgerEntry)
    4. Proposes course when bucket threshold is met

    Args:
        student_id: Student UUID
        lesson_id: Lesson UUID
        track: Track enum value (CREATION_SCIENCE, etc.)
        lesson_title: Human-readable lesson title
        estimated_minutes: Time engaged in lesson
        mastery_score: 0.0–1.0 mastery assessment
        activity_date: When the lesson was completed
        prisma: Prisma async client for DB writes
    """
    bucket = TRACK_BUCKET_MAP.get(track)
    if not bucket:
        return

    # Load profile (default to flexible homeschool)
    profiles = _load_profiles()
    profile_key = "oklahoma_flexible_homeschool"
    profile_data = profiles[profile_key]

    # 1. Map lesson to OAS standards and record
    oas_standards = map_lesson_to_oas(track=track, content=lesson_title, grade_band="9-12")
    for oas in oas_standards:
        await prisma.standardsledgerentry.create(
            data={
                "studentId": student_id,
                "framework": "OAS",
                "subject": oas.subject.value,
                "code": oas.code,
                "confidence": oas.confidence,
                "lessonId": lesson_id,
            }
        )

    # 2. Record evidence
    hours_engaged = estimated_minutes / 60.0
    evidence_entry = await prisma.evidenceledgerentry.create(
        data={
            "studentId": student_id,
            "artifactType": "project",
            "title": lesson_title,
            "masteryScore": mastery_score,
            "hours": hours_engaged,
            "activityDate": activity_date,
            "evaluatorNotes": f"From lesson: {lesson_id}",
            "bucket": bucket,
        }
    )

    # 3. Accumulate credit hours
    weighting = apply_profile_weighting(profile_key, profile_data)
    mastery_factor = 0.5 + (mastery_score * 0.5)
    weighted_hours = hours_engaged * weighting.project * mastery_factor

    await prisma.creditledgerentry.create(
        data={
            "studentId": student_id,
            "bucket": bucket,
            "hoursEarned": weighted_hours,
            "source": "lesson",
            "sourceId": lesson_id,
        }
    )

    # 4. Check threshold and propose course
    all_credit_entries = await prisma.creditledgerentry.find_many(
        where={"studentId": student_id, "bucket": bucket}
    )
    total_hours = sum(e.hoursEarned for e in all_credit_entries)

    full_threshold = profile_data["creditThresholds"]["full_credit"]
    half_threshold = profile_data["creditThresholds"]["half_credit"]

    credit_earned = None
    if total_hours >= full_threshold:
        credit_earned = 1.0
    elif total_hours >= half_threshold:
        credit_earned = 0.5

    if credit_earned:
        existing_proposal = await prisma.evidenceledgerentry.find_first(
            where={
                "studentId": student_id,
                "bucket": bucket,
                "proposedCourse": {"not": None},
            }
        )
        if not existing_proposal:
            external_name = TRACK_EXTERNAL_NAME.get(track, track)
            await prisma.evidenceledgerentry.update(
                where={"id": evidence_entry.id},
                data={"proposedCourse": external_name},
            )
