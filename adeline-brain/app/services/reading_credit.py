"""
Reading evidence service — preserves a finished book and learner reflection.

Pure functions (calculate_reading_credit, get_reading_standards) have NO database
calls.  award_reading_credit() is the async entry point that writes ledger rows.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

# ── Grade-to-Lexile ranges ──────────────────────────────────────────────────

GRADE_LEXILE_RANGES: dict[int, tuple[int, int]] = {
    0:  (250, 350),   # Kindergarten
    1:  (300, 400),
    2:  (400, 500),
    3:  (500, 600),
    4:  (600, 700),
    5:  (650, 750),
    6:  (700, 800),
    7:  (750, 850),
    8:  (800, 900),
    9:  (850, 950),
    10: (900, 1000),
    11: (950, 1050),
    12: (1000, 1100),
}

# ── Track → Graduation Bucket ───────────────────────────────────────────────

TRACK_TO_GRADUATION_BUCKET: dict[str, str] = {
    "ENGLISH_LITERATURE":    "ENGLISH_CORE",
    "TRUTH_HISTORY":         "SOCIAL_STUDIES",
    "JUSTICE_CHANGEMAKING":  "SOCIAL_STUDIES",
    "GOVERNMENT_ECONOMICS":  "SOCIAL_STUDIES",
    "CREATION_SCIENCE":      "SCIENCE_CORE",
    "HOMESTEADING":          "SCIENCE_CORE",
    "HEALTH_NATUROPATHY":    "SCIENCE_CORE",
    "APPLIED_MATHEMATICS":   "MATH_CORE",
    "DISCIPLESHIP":          "ELECTIVES",
    "CREATIVE_ECONOMY":      "FINE_ARTS",
}

# Literature tracks use RL (Reading Literature) standards; others use RI (Reading Informational).
_LITERATURE_TRACKS = {"ENGLISH_LITERATURE", "DISCIPLESHIP"}


# ── Pure functions ───────────────────────────────────────────────────────────

def calculate_reading_credit(
    reading_minutes: float,
    book_lexile: int,
    grade_level: int,
) -> float:
    """
    Conventional Carnegie-time equivalency estimate for family records.

    Formula: (reading_minutes / 60) / 120 * lexile_multiplier
      - 120 is the Carnegie-unit hour target (one credit = 120 clock hours).
      - Multiplier rewards stretch reading and discounts below-grade books.

    This value is descriptive only. It must never establish mastery, standards
    completion, course credit, or graduation progress.
    """
    if reading_minutes <= 0:
        return 0.0

    grade_min, grade_max = GRADE_LEXILE_RANGES.get(grade_level, (700, 800))

    if book_lexile > grade_max:
        multiplier = 1.2
    elif book_lexile < grade_min:
        multiplier = 0.8
    else:
        multiplier = 1.0

    return (reading_minutes / 60) / 120 * multiplier


def get_reading_standards(track: str, grade_num: int) -> list[str]:
    """
    Return 1-2 CCSS-style reading standards for K-8 students.

    Grades 9+ return an empty list (high-school standards are course-based,
    not grade-banded).

    Literature tracks use RL (Reading Literature); all others use RI
    (Reading Informational Text).
    """
    if grade_num > 8:
        return []

    prefix = "RL" if track in _LITERATURE_TRACKS else "RI"
    return [f"{prefix}.{grade_num}.2", f"{prefix}.{grade_num}.10"]


# ── Async ledger writer ─────────────────────────────────────────────────────

async def award_reading_credit(
    session_id: str,
    student_id: str,
    book_id: str,
    book_title: str,
    book_track: str,
    book_lexile: int,
    reading_minutes: float,
    student_reflection: str,
    grade_level: int,
    completed_at: Optional[datetime] = None,
) -> dict:
    """
    Idempotently preserve evidence for a completed reading session.

    Reading time and book difficulty remain descriptive metadata. A finished
    book plus an unreviewed reflection is not automatically 100% mastery, so
    this path does not write credit or standards-mastery ledger rows.

    Returns a summary dict with IDs and hours.
    """
    from app.config import get_db_conn

    completed_at = completed_at or datetime.now(timezone.utc)
    conn = await get_db_conn()

    try:
        # ── Idempotency check ────────────────────────────────────────────
        evidence_note = f"reading-session:{session_id}\n{student_reflection}"
        existing = await conn.fetchval(
            'SELECT id FROM "EvidenceLedgerEntry" WHERE "studentId" = $1 AND "evaluatorNotes" = $2',
            student_id,
            evidence_note,
        )
        if existing:
            return {"already_recorded": True, "evidence_id": existing, "credit_hours": 0.0}

        # ── Compute credit hours ─────────────────────────────────────────
        conventional_equivalency = calculate_reading_credit(reading_minutes, book_lexile, grade_level)
        bucket = TRACK_TO_GRADUATION_BUCKET.get(book_track, "ELECTIVES")

        # ── Evidence ledger ──────────────────────────────────────────────
        evidence_id = str(uuid.uuid4())
        await conn.execute(
            'INSERT INTO "EvidenceLedgerEntry" '
            '(id, "studentId", "artifactType", title, "masteryScore", hours, '
            '"activityDate", "evaluatorNotes", bucket, "isApproved", "createdAt") '
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)",
            evidence_id,
            student_id,
            "reading",
            book_title,
            0.0,           # pending review; completion is not mastery
            conventional_equivalency,
            completed_at,
            evidence_note,
            bucket,
            False,
            datetime.now(timezone.utc),
        )

        return {
            "already_recorded": False,
            "evidence_id": evidence_id,
            "credit_hours": 0.0,
            "conventional_equivalency": conventional_equivalency,
            "bucket": bucket,
            "mastery_status": "PENDING_REVIEW",
        }
    finally:
        await conn.close()
