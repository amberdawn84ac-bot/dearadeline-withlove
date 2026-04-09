"""
Reading credit service — awards transcript credit when a student finishes a book.

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
    Credit hours earned from a completed book.

    Formula: (reading_minutes / 60) / 120 * lexile_multiplier
      - 120 is the Carnegie-unit hour target (one credit = 120 clock hours).
      - Multiplier rewards stretch reading and discounts below-grade books.

    Returns 0.0 when reading_minutes is zero or negative.
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
    Idempotently award credit for a completed reading session.

    Writes three ledger tables:
      1. EvidenceLedgerEntry  — the reading artifact
      2. CreditLedgerEntry    — hours in the graduation bucket
      3. StandardsLedgerEntry — CCSS reading standards (K-8 only)

    Returns a summary dict with IDs and hours.
    """
    from app.config import get_db_conn

    completed_at = completed_at or datetime.now(timezone.utc)
    conn = await get_db_conn()

    try:
        # ── Idempotency check ────────────────────────────────────────────
        existing = await conn.fetchval(
            'SELECT id FROM "CreditLedgerEntry" '
            "WHERE source = 'reading' AND \"sourceId\" = $1",
            session_id,
        )
        if existing:
            return {"already_awarded": True, "credit_id": existing}

        # ── Compute credit hours ─────────────────────────────────────────
        hours = calculate_reading_credit(reading_minutes, book_lexile, grade_level)
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
            1.0,           # mastery — completed book with reflection
            hours,
            completed_at,
            student_reflection,
            bucket,
            True,
            datetime.now(timezone.utc),
        )

        # ── Credit ledger ────────────────────────────────────────────────
        credit_id = str(uuid.uuid4())
        await conn.execute(
            'INSERT INTO "CreditLedgerEntry" '
            '(id, "studentId", bucket, "hoursEarned", source, "sourceId", "createdAt") '
            "VALUES ($1,$2,$3,$4,$5,$6,$7)",
            credit_id,
            student_id,
            bucket,
            hours,
            "reading",
            session_id,
            datetime.now(timezone.utc),
        )

        # ── Standards ledger (K-8 only) ──────────────────────────────────
        standards = get_reading_standards(book_track, grade_level)
        standard_ids = []
        for code in standards:
            sid = str(uuid.uuid4())
            standard_ids.append(sid)
            await conn.execute(
                'INSERT INTO "StandardsLedgerEntry" '
                '(id, "studentId", framework, subject, code, confidence, '
                '"lessonId", "addressedAt", "createdAt") '
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)",
                sid,
                student_id,
                "CCSS",
                "ELA",
                code,
                0.8,        # default confidence for completed reading
                None,       # no lesson — this is a reading session
                completed_at,
                datetime.now(timezone.utc),
            )

        return {
            "already_awarded": False,
            "evidence_id": evidence_id,
            "credit_id": credit_id,
            "standard_ids": standard_ids,
            "hours": hours,
            "bucket": bucket,
        }
    finally:
        await conn.close()
