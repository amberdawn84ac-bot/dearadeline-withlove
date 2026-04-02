"""
GPA Calculator — credit-weighted GPA per CEEB standard.
Pure function: no DB calls, no side effects.
"""
from enum import Enum
from typing import NamedTuple


class GradeLetter(str, Enum):
    A_PLUS = "A_PLUS"
    A = "A"
    A_MINUS = "A_MINUS"
    B_PLUS = "B_PLUS"
    B = "B"
    B_MINUS = "B_MINUS"
    C_PLUS = "C_PLUS"
    C = "C"
    C_MINUS = "C_MINUS"
    D_PLUS = "D_PLUS"
    D = "D"
    D_MINUS = "D_MINUS"
    F = "F"
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


class GPACalculation(NamedTuple):
    cumulativeGPA: float
    creditsAttempted: float
    creditsEarned: float
    creditsEarnedFromPassing: float


GRADE_POINTS: dict[GradeLetter, float] = {
    GradeLetter.A_PLUS: 4.0,
    GradeLetter.A: 4.0,
    GradeLetter.A_MINUS: 3.7,
    GradeLetter.B_PLUS: 3.3,
    GradeLetter.B: 3.0,
    GradeLetter.B_MINUS: 2.7,
    GradeLetter.C_PLUS: 2.3,
    GradeLetter.C: 2.0,
    GradeLetter.C_MINUS: 1.7,
    GradeLetter.D_PLUS: 1.3,
    GradeLetter.D: 1.0,
    GradeLetter.D_MINUS: 0.7,
    GradeLetter.F: 0.0,
    GradeLetter.PASS: 0.0,
    GradeLetter.FAIL: 0.0,
    GradeLetter.INCOMPLETE: 0.0,
}


def calculate_gpa(transcript_entries: list[dict]) -> GPACalculation:
    total_quality_points = 0.0
    total_attempted = 0.0
    total_earned = 0.0
    total_earned_pass_fail = 0.0

    for entry in transcript_entries:
        hours = float(entry.get("creditHours", 0.0))
        grade_raw = entry.get("gradeLetter", "")

        if isinstance(grade_raw, str):
            try:
                grade = GradeLetter[grade_raw]
            except KeyError:
                grade = GradeLetter.F
        else:
            grade = grade_raw

        if hours <= 0:
            continue

        total_attempted += hours

        if grade == GradeLetter.FAIL or grade == GradeLetter.INCOMPLETE:
            pass
        elif grade == GradeLetter.PASS:
            total_earned_pass_fail += hours
        else:
            points = GRADE_POINTS.get(grade, 0.0)
            total_quality_points += hours * points
            total_earned += hours

    if total_earned > 0:
        cumulative_gpa = round(total_quality_points / total_earned, 2)
    else:
        cumulative_gpa = 0.0

    return GPACalculation(
        cumulativeGPA=cumulative_gpa,
        creditsAttempted=round(total_attempted, 1),
        creditsEarned=round(total_earned, 1),
        creditsEarnedFromPassing=round(total_earned_pass_fail, 1),
    )


def format_gpa(gpa_value: float) -> str:
    return f"{gpa_value:.2f}"
