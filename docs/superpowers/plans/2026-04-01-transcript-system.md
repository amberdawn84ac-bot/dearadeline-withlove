# Transcript System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate two document types — Official Transcript (conventional PDF) and Mastery Portfolio (rich course descriptions) — with an OSRHE 15-unit college-prep dashboard showing progress toward Oklahoma's graduation requirements.

**Architecture:** Python PDF generation in adeline-brain using reportlab. Course titles always use TRACK_CREDIT_MAP external names (e.g., "Environmental Science" instead of "HOMESTEADING"). Only parent-approved courses appear on the official transcript. OSRHE dashboard tracks progress against Oklahoma's 15-unit core requirement (4 English, 3 Lab Science, 3 Math, 3 History/Citizenship, 2 Additional approved).

**Tech Stack:** Python (FastAPI, reportlab for PDF), TypeScript (Next.js 14 App Router), existing Prisma TranscriptEntry + CreditLedgerEntry models, TRACK_CREDIT_MAP from adeline-core.

**Depends on:** Plan C (Standards & Credits Engine) — course approval flow must exist before this can write approved courses to the official transcript PDF.

**Status:** Ready for implementation. Existing `/transcripts/generate/{student_id}` endpoint in adeline-brain is foundation; this plan enhances with mastery portfolio, GPA calculation, and OSRHE dashboard.

---

## Implementation Tasks

### Task 1: GPA Calculation Utility (Pure Function)

**Goal:** Create a reusable GPA calculator following standard 4.0 scale with credit-weighted averaging.

**Grading Scale:**
- A+: 4.0, A: 4.0, A−: 3.7
- B+: 3.3, B: 3.0, B−: 2.7
- C+: 2.3, C: 2.0, C−: 1.7
- D+: 1.3, D: 1.0, D−: 0.7
- F: 0.0
- PASS/FAIL: not included in GPA, but recorded as mastery

**File:** `adeline-brain/app/services/gpa_calculator.py`

```python
"""
GPA Calculator — credit-weighted GPA per CEEB standard.
Tests in: adeline-brain/tests/test_gpa_calculator.py

Design:
- Pure function: no DB calls, no side effects
- Input: list of (creditHours: float, gradeLetter: GradeLetter)
- Output: (cumulativeGPA: float, creditsAttempted: float, creditsEarned: float)
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


# CEEB 4.0 scale mapping
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
    # Pass/Fail not included in GPA but do count toward credits
    GradeLetter.PASS: 0.0,  # No grade points
    GradeLetter.FAIL: 0.0,  # No grade points
    GradeLetter.INCOMPLETE: 0.0,  # No grade points
}


def calculate_gpa(
    transcript_entries: list[dict],
) -> GPACalculation:
    """
    Calculate cumulative GPA from a list of transcript entries.

    Args:
        transcript_entries: List of dicts with keys:
            - creditHours: float
            - gradeLetter: str or GradeLetter enum
            - courseTitle: str (for logging)

    Returns:
        GPACalculation with (cumulativeGPA, creditsAttempted, creditsEarned, creditsEarnedFromPassing)

    Rules:
    - PASS/FAIL grades are not counted in GPA but count toward credits earned
    - INCOMPLETE courses count as attempted but not earned
    - Weighted average: sum(hours * points) / sum(hours)
    - Round to 2 decimals (e.g. 3.67)
    """

    total_quality_points = 0.0
    total_attempted = 0.0
    total_earned = 0.0
    total_earned_pass_fail = 0.0

    for entry in transcript_entries:
        hours = float(entry.get("creditHours", 0.0))
        grade_raw = entry.get("gradeLetter", "")

        # Convert string to enum if needed
        if isinstance(grade_raw, str):
            try:
                grade = GradeLetter[grade_raw]
            except KeyError:
                # Fallback: treat unknown grades as F
                grade = GradeLetter.F
        else:
            grade = grade_raw

        # Skip invalid entries
        if hours <= 0:
            continue

        total_attempted += hours

        # Determine credit earned and quality points
        if grade == GradeLetter.FAIL or grade == GradeLetter.INCOMPLETE:
            # No credit earned, no quality points
            pass
        elif grade == GradeLetter.PASS:
            # Credit earned but no GPA impact
            total_earned_pass_fail += hours
        else:
            # Regular grade: apply quality points
            points = GRADE_POINTS.get(grade, 0.0)
            total_quality_points += hours * points
            total_earned += hours

    # Calculate cumulative GPA
    if total_earned > 0:
        cumulative_gpa = round(total_quality_points / total_earned, 2)
    else:
        cumulative_gpa = 0.0

    total_earned_all = total_earned + total_earned_pass_fail

    return GPACalculation(
        cumulativeGPA=cumulative_gpa,
        creditsAttempted=round(total_attempted, 1),
        creditsEarned=round(total_earned, 1),
        creditsEarnedFromPassing=round(total_earned_pass_fail, 1),
    )


def format_gpa(gpa_value: float) -> str:
    """Format a GPA value to 2 decimal places."""
    return f"{gpa_value:.2f}"
```

**Unit Tests:** `adeline-brain/tests/test_gpa_calculator.py`

```python
import pytest
from app.services.gpa_calculator import calculate_gpa, GradeLetter, format_gpa


def test_calculate_gpa_all_a_grades():
    """Perfect 4.0 GPA."""
    entries = [
        {"creditHours": 3.0, "gradeLetter": "A", "courseTitle": "English I"},
        {"creditHours": 4.0, "gradeLetter": "A", "courseTitle": "Lab Science"},
        {"creditHours": 3.0, "gradeLetter": "A", "courseTitle": "Math"},
    ]
    result = calculate_gpa(entries)
    assert result.cumulativeGPA == 4.0
    assert result.creditsAttempted == 10.0
    assert result.creditsEarned == 10.0


def test_calculate_gpa_mixed_grades():
    """Mixed grades with weighted average."""
    entries = [
        {"creditHours": 4.0, "gradeLetter": "A", "courseTitle": "English"},  # 4.0 * 4 = 16.0
        {"creditHours": 3.0, "gradeLetter": "B", "courseTitle": "History"},   # 3.0 * 3 = 9.0
        {"creditHours": 3.0, "gradeLetter": "C", "courseTitle": "Elective"},  # 2.0 * 3 = 6.0
    ]
    result = calculate_gpa(entries)
    # Total points: 16.0 + 9.0 + 6.0 = 31.0
    # Total hours: 10.0
    # GPA: 31.0 / 10.0 = 3.1
    assert result.cumulativeGPA == 3.1
    assert result.creditsEarned == 10.0


def test_calculate_gpa_with_pass_fail():
    """PASS grades earn credit but don't impact GPA."""
    entries = [
        {"creditHours": 4.0, "gradeLetter": "A", "courseTitle": "English"},  # 16.0 quality pts
        {"creditHours": 2.0, "gradeLetter": "PASS", "courseTitle": "PE"},      # 0 quality pts, 2.0 earned
    ]
    result = calculate_gpa(entries)
    # GPA: 16.0 / 4.0 = 4.0 (PASS doesn't factor in)
    assert result.cumulativeGPA == 4.0
    assert result.creditsEarned == 4.0
    assert result.creditsEarnedFromPassing == 2.0


def test_calculate_gpa_with_failures():
    """FAIL courses attempted but not earned."""
    entries = [
        {"creditHours": 3.0, "gradeLetter": "A", "courseTitle": "English"},    # 12.0 quality pts
        {"creditHours": 3.0, "gradeLetter": "F", "courseTitle": "Failed Math"},  # 0 quality pts, 0 earned
    ]
    result = calculate_gpa(entries)
    # GPA: 12.0 / 3.0 = 4.0 (F doesn't factor in)
    assert result.cumulativeGPA == 4.0
    assert result.creditsAttempted == 6.0
    assert result.creditsEarned == 3.0


def test_calculate_gpa_empty_list():
    """No entries returns 0.0 GPA."""
    result = calculate_gpa([])
    assert result.cumulativeGPA == 0.0
    assert result.creditsAttempted == 0.0
    assert result.creditsEarned == 0.0


def test_format_gpa():
    """GPA formatting to 2 decimal places."""
    assert format_gpa(3.6666) == "3.67"
    assert format_gpa(4.0) == "4.00"
    assert format_gpa(0.0) == "0.00"
```

**Checklist:**
- [ ] Create `adeline-brain/app/services/gpa_calculator.py` with all functions
- [ ] Create `adeline-brain/tests/test_gpa_calculator.py` with test suite
- [ ] Run tests: `pytest adeline-brain/tests/test_gpa_calculator.py -v`
- [ ] Verify all tests pass

---

### Task 2: Official Transcript PDF Generator

**Goal:** Enhanced PDF generation with GPA, approved course list, and professional formatting.

**File:** `adeline-brain/app/services/transcript_pdf.py`

**Build on existing:** The existing `_build_pdf()` in `transcripts.py` is the foundation. Refactor into a dedicated service with these additions:
- Calculate cumulative GPA from TranscriptEntry records
- Filter courses: only include `isApproved=True` entries
- Display course title, year, credit hours, grade, and grade points per course
- Show cumulative GPA at bottom
- Add grading scale legend

```python
"""
Official Transcript PDF Generator — CEEB-compliant academic record.

Generates a printable PDF transcript with:
- Course list (approved courses only)
- GPA calculation
- Grading scale
- Registrar's seal

Design:
- Takes student_id, fetches TranscriptEntry + CreditLedger data
- Filters for isApproved=True entries
- Calls gpa_calculator for cumulative GPA
- Returns bytes (streamable)
"""

import io
import logging
from datetime import datetime, date
from typing import Optional

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak,
)

from app.services.gpa_calculator import calculate_gpa, GradeLetter, format_gpa
from app.schemas.api_models import TranscriptEntry, User

logger = logging.getLogger(__name__)

# ─ Color palette (match adeline-core theme) ─────────────────────────────────
INK    = colors.HexColor("#2C2318")  # Deep brown
PARA   = colors.HexColor("#9A3F4A")  # Paradise wine
ACCENT = colors.HexColor("#BD6809")  # Papaya gold


def build_official_transcript_pdf(
    student: dict,
    transcript_entries: list[dict],
    school_name: str = "Dear Adeline Classical Academy",
    school_address: str = "Oklahoma",
    generated_date: Optional[datetime] = None,
) -> bytes:
    """
    Generate an official academic transcript PDF.

    Args:
        student: {id, name, gradeLevel, createdAt, ...}
        transcript_entries: List of approved TranscriptEntry dicts with:
            - courseTitle (external name from TRACK_CREDIT_MAP)
            - creditHours
            - gradeLetter
            - percentScore (optional)
            - completedAt or year
            - track (for filtering/organization)
        school_name: School name (default: Dear Adeline Classical Academy)
        school_address: School address (default: Oklahoma)
        generated_date: Override generation date (for testing)

    Returns:
        PDF as bytes
    """

    generated_date = generated_date or datetime.now()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=1.0 * inch,
        rightMargin=1.0 * inch,
        topMargin=1.0 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    # ─ Style definitions ────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title",
        fontName="Times-Bold",
        fontSize=16,
        textColor=INK,
        spaceAfter=2,
        alignment=1,  # center
    )

    sub_title_style = ParagraphStyle(
        "SubTitle",
        fontName="Times-Roman",
        fontSize=11,
        textColor=INK,
        spaceAfter=1,
        alignment=1,
    )

    section_style = ParagraphStyle(
        "Section",
        fontName="Times-Bold",
        fontSize=11,
        textColor=PARA,
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "Body",
        fontName="Times-Roman",
        fontSize=10,
        textColor=INK,
        spaceAfter=4,
        leading=12,
    )

    small_style = ParagraphStyle(
        "Small",
        fontName="Times-Roman",
        fontSize=9,
        textColor=INK,
        spaceAfter=2,
        leading=10,
    )

    italic_style = ParagraphStyle(
        "Italic",
        fontName="Times-Italic",
        fontSize=9,
        textColor=INK,
        spaceAfter=2,
        leading=10,
    )

    # ─ Header: School and Student Info ──────────────────────────────────────
    story.append(Paragraph(school_name, title_style))
    story.append(Paragraph(school_address, sub_title_style))
    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="100%", thickness=2, color=PARA))
    story.append(Spacer(1, 0.15 * inch))

    # Student info table
    student_info = [
        ["Student Name:", student.get("name", "")],
        ["Student ID:", student.get("id", "")[:8]],
        ["Grade Level:", student.get("gradeLevel", "")],
        ["Generated:", generated_date.strftime("%B %d, %Y")],
    ]

    info_table = Table(student_info, colWidths=[1.5 * inch, 3.5 * inch])
    info_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (0, -1), "Times-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.2 * inch))

    # ─ Filter approved courses ──────────────────────────────────────────────
    # This assumes the entries are already filtered server-side,
    # but we double-check here
    approved_entries = [
        e for e in transcript_entries
        if e.get("isApproved", True)  # Default to True if not specified
    ]

    if not approved_entries:
        story.append(Paragraph(
            "No approved courses to display.",
            body_style,
        ))
        doc.build(story)
        buf.seek(0)
        return buf.read()

    # ─ Course Table ─────────────────────────────────────────────────────────
    story.append(Paragraph("COURSE RECORD", section_style))

    # Header row
    course_rows = [[
        Paragraph("<b>Course Title</b>", body_style),
        Paragraph("<b>Year</b>", body_style),
        Paragraph("<b>Credits</b>", body_style),
        Paragraph("<b>Grade</b>", body_style),
        Paragraph("<b>Points</b>", body_style),
    ]]

    total_credits_attempted = 0.0
    for entry in approved_entries:
        title = entry.get("courseTitle", "Untitled")
        year_completed = entry.get("completedAt")
        if isinstance(year_completed, str):
            try:
                year_completed = datetime.fromisoformat(year_completed.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                year_completed = None
        year_str = year_completed.strftime("%Y") if year_completed else "—"

        credits = float(entry.get("creditHours", 0.0))
        grade_letter = entry.get("gradeLetter", "")

        # Get grade points
        try:
            grade_enum = GradeLetter[grade_letter] if isinstance(grade_letter, str) else grade_letter
            grade_points = {
                GradeLetter.A_PLUS: 4.0, GradeLetter.A: 4.0, GradeLetter.A_MINUS: 3.7,
                GradeLetter.B_PLUS: 3.3, GradeLetter.B: 3.0, GradeLetter.B_MINUS: 2.7,
                GradeLetter.C_PLUS: 2.3, GradeLetter.C: 2.0, GradeLetter.C_MINUS: 1.7,
                GradeLetter.D_PLUS: 1.3, GradeLetter.D: 1.0, GradeLetter.D_MINUS: 0.7,
                GradeLetter.F: 0.0,
                GradeLetter.PASS: 0.0, GradeLetter.FAIL: 0.0, GradeLetter.INCOMPLETE: 0.0,
            }.get(grade_enum, 0.0)
        except (KeyError, AttributeError):
            grade_points = 0.0

        quality_points_str = f"{credits * grade_points:.1f}" if grade_points > 0 else "—"
        total_credits_attempted += credits

        course_rows.append([
            Paragraph(title, small_style),
            Paragraph(year_str, small_style),
            Paragraph(f"{credits:.1f}", small_style),
            Paragraph(grade_letter, small_style),
            Paragraph(quality_points_str, small_style),
        ])

    course_table = Table(
        course_rows,
        colWidths=[3.0 * inch, 0.8 * inch, 0.9 * inch, 0.7 * inch, 0.8 * inch],
    )
    course_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0D9B0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E3C07A")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FDF8F0")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(course_table)
    story.append(Spacer(1, 0.15 * inch))

    # ─ GPA Calculation ──────────────────────────────────────────────────────
    gpa_result = calculate_gpa(approved_entries)

    gpa_info = [
        ["Total Credits Attempted:", f"{gpa_result.creditsAttempted:.1f}"],
        ["Total Credits Earned:", f"{gpa_result.creditsEarned:.1f}"],
        ["Cumulative GPA:", f"{format_gpa(gpa_result.cumulativeGPA)}"],
    ]

    gpa_table = Table(gpa_info, colWidths=[2.5 * inch, 1.5 * inch])
    gpa_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (0, -1), "Times-Bold"),
        ("FONTNAME", (1, -1), (1, -1), "Times-Bold"),
        ("FONTSIZE", (0, -1), (1, -1), 11),
        ("FONTSIZE", (0, 0), (0, -2), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F0D9B0")),
    ]))
    story.append(gpa_table)
    story.append(Spacer(1, 0.2 * inch))

    # ─ Grading Scale Legend ─────────────────────────────────────────────────
    story.append(Paragraph("GRADING SCALE", section_style))

    scale_data = [
        ["Grade", "Scale", "Grade", "Scale", "Grade", "Scale"],
        ["A+", "4.0", "B−", "2.7", "D", "1.0"],
        ["A", "4.0", "C+", "2.3", "D−", "0.7"],
        ["A−", "3.7", "C", "2.0", "F", "0.0"],
        ["B+", "3.3", "C−", "1.7", "PASS", "—"],
        ["B", "3.0", "D+", "1.3", "FAIL", "—"],
    ]

    scale_table = Table(scale_data, colWidths=[1.0 * inch, 1.0 * inch] * 3)
    scale_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0D9B0")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E3C07A")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(scale_table)
    story.append(Spacer(1, 0.2 * inch))

    # ─ Registrar Seal ───────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        "REGISTRAR'S CERTIFICATION",
        ParagraphStyle(
            "Seal",
            fontName="Times-Bold",
            fontSize=10,
            textColor=ACCENT,
        ),
    ))
    story.append(Paragraph(
        "This is an official academic record of coursework completed and academic achievement. "
        "All courses listed reflect verified learning through the Witness Protocol (cosine similarity ≥ 0.82). "
        "This transcript may be submitted in fulfillment of college admissions requirements.",
        italic_style,
    ))
    story.append(Spacer(1, 0.4 * inch))

    # Signature lines
    sig_table = Table(
        [
            ["_____________________", "", "_____________________"],
            ["Registrar Signature", "", "Date"],
        ],
        colWidths=[2.0 * inch, 1.0 * inch, 2.0 * inch],
    )
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
    ]))
    story.append(sig_table)

    # Footer
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        "Dear Adeline Classical Academy — Truth-First K-12 Learning Companion",
        italic_style,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
```

**Checklist:**
- [ ] Create `adeline-brain/app/services/transcript_pdf.py` with `build_official_transcript_pdf()` function
- [ ] Update imports in `adeline-brain/app/api/transcripts.py` to use new service
- [ ] Create `adeline-brain/tests/test_transcript_pdf.py` with sample PDF generation tests
- [ ] Run tests: `pytest adeline-brain/tests/test_transcript_pdf.py -v`

---

### Task 3: Mastery Portfolio Generator

**Goal:** Create a detailed "course descriptions" PDF showing what the student learned, primary texts, projects, standards, and grading methods.

**File:** `adeline-brain/app/services/portfolio_generator.py`

This document is *richer* than the official transcript. Each course gets a full page with:
- Course description (why this course matters)
- Major texts and primary sources studied
- Projects, labs, and presentations completed
- Standards addressed
- Grading method (Witness Protocol, xAPI, etc.)

```python
"""
Mastery Portfolio Generator — Rich course descriptions and learning evidence.

Creates a multi-page PDF showing:
- Course descriptions
- Learning outcomes per course
- Primary sources / texts studied
- Projects and evidence artifacts
- Standards mastery
- Assessment method

Design:
- Reads TranscriptEntry + LearningRecord + Evidence tables
- Organizes by approved course
- Generates one page per course
- Returns bytes (streamable)
"""

import io
import logging
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    HRFlowable,
)

logger = logging.getLogger(__name__)

# ─ Color palette ────────────────────────────────────────────────────────────
INK    = colors.HexColor("#2C2318")
PARA   = colors.HexColor("#9A3F4A")
ACCENT = colors.HexColor("#BD6809")


def build_mastery_portfolio_pdf(
    student: dict,
    portfolio_data: list[dict],
    school_name: str = "Dear Adeline Classical Academy",
    generated_date: Optional[datetime] = None,
) -> bytes:
    """
    Generate a mastery portfolio PDF with course descriptions.

    Args:
        student: {id, name, gradeLevel, ...}
        portfolio_data: List of course portfolio entries, each with:
            - courseTitle: str
            - track: str (internal track enum)
            - description: str (why this course matters)
            - learningOutcomes: list[str]
            - primaryTexts: list[dict] = [{"title": str, "author": str, "year": int}, ...]
            - projects: list[dict] = [{"title": str, "description": str, "completedAt": datetime}, ...]
            - oasStandards: list[str]
            - gradingMethod: str (e.g., "Witness Protocol + xAPI + Student Artifacts")
            - masteryScore: float (0.0 to 1.0)
        school_name: School name
        generated_date: Override generation date

    Returns:
        PDF as bytes
    """

    generated_date = generated_date or datetime.now()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story = []

    # ─ Style definitions ────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title",
        fontName="Times-Bold",
        fontSize=18,
        textColor=INK,
        spaceAfter=2,
        alignment=1,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        fontName="Times-Italic",
        fontSize=12,
        textColor=PARA,
        spaceAfter=4,
        alignment=1,
    )

    course_title_style = ParagraphStyle(
        "CourseTitle",
        fontName="Times-Bold",
        fontSize=14,
        textColor=PARA,
        spaceBefore=6,
        spaceAfter=6,
    )

    section_heading_style = ParagraphStyle(
        "SectionHeading",
        fontName="Times-Bold",
        fontSize=11,
        textColor=ACCENT,
        spaceBefore=8,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "Body",
        fontName="Times-Roman",
        fontSize=10,
        textColor=INK,
        spaceAfter=3,
        leading=13,
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        fontName="Times-Roman",
        fontSize=10,
        textColor=INK,
        spaceAfter=2,
        leading=12,
        leftIndent=0.25 * inch,
    )

    small_style = ParagraphStyle(
        "Small",
        fontName="Times-Roman",
        fontSize=9,
        textColor=INK,
        spaceAfter=2,
        leading=11,
    )

    # ─ Cover page ───────────────────────────────────────────────────────────
    story.append(Paragraph("MASTERY PORTFOLIO", title_style))
    story.append(Paragraph(
        f"A Record of Learning & Achievement",
        subtitle_style,
    ))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph(f"Student: {student.get('name', '')}", body_style))
    story.append(Paragraph(f"ID: {student.get('id', '')[:8]}", body_style))
    story.append(Paragraph(f"Grade: {student.get('gradeLevel', '')}", body_style))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph(f"School: {school_name}", small_style))
    story.append(Paragraph(
        f"Generated: {generated_date.strftime('%B %d, %Y')}",
        small_style,
    ))
    story.append(Spacer(1, 0.4 * inch))

    story.append(HRFlowable(width="100%", thickness=1, color=PARA))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(
        "This portfolio documents the student\u2019s demonstrated mastery of content "
        "through primary source study, project-based learning, and authentic assessment. "
        "Each course represents verified learning (Witness Protocol ≥ 0.82 confidence).",
        body_style,
    ))

    # ─ Course Pages ─────────────────────────────────────────────────────────
    for i, course in enumerate(portfolio_data):
        if i > 0:  # Page break before each course (except first)
            story.append(PageBreak())

        # Course title
        story.append(Paragraph(course.get("courseTitle", "Untitled Course"), course_title_style))

        # Track label (small)
        track = course.get("track", "")
        story.append(Paragraph(f"<i>{track}</i>", small_style))
        story.append(Spacer(1, 0.1 * inch))

        # Course description
        if course.get("description"):
            story.append(Paragraph("COURSE DESCRIPTION", section_heading_style))
            story.append(Paragraph(course["description"], body_style))
            story.append(Spacer(1, 0.08 * inch))

        # Learning outcomes
        if course.get("learningOutcomes"):
            story.append(Paragraph("LEARNING OUTCOMES", section_heading_style))
            for outcome in course["learningOutcomes"]:
                story.append(Paragraph(f"• {outcome}", bullet_style))
            story.append(Spacer(1, 0.08 * inch))

        # Primary texts / readings
        if course.get("primaryTexts"):
            story.append(Paragraph("PRIMARY TEXTS & READINGS", section_heading_style))
            for text in course["primaryTexts"]:
                title = text.get("title", "")
                author = text.get("author", "")
                year = text.get("year", "")
                cite_parts = [title]
                if author:
                    cite_parts.append(f"by {author}")
                if year:
                    cite_parts.append(f"({year})")
                cite = " — ".join(cite_parts)
                story.append(Paragraph(f"• {cite}", bullet_style))
            story.append(Spacer(1, 0.08 * inch))

        # Projects and presentations
        if course.get("projects"):
            story.append(Paragraph("PROJECTS & PRESENTATIONS", section_heading_style))
            for project in course["projects"]:
                proj_title = project.get("title", "")
                proj_desc = project.get("description", "")
                completed = project.get("completedAt")
                date_str = ""
                if isinstance(completed, str):
                    try:
                        dt = datetime.fromisoformat(completed.replace("Z", "+00:00"))
                        date_str = f" ({dt.strftime('%b %Y')})"
                    except (ValueError, TypeError):
                        pass

                story.append(Paragraph(f"• {proj_title}{date_str}", bullet_style))
                if proj_desc:
                    desc_style = ParagraphStyle(
                        "ProjectDesc",
                        fontName="Times-Roman",
                        fontSize=9,
                        textColor=INK,
                        spaceAfter=2,
                        leading=11,
                        leftIndent=0.5 * inch,
                    )
                    story.append(Paragraph(proj_desc, desc_style))
            story.append(Spacer(1, 0.08 * inch))

        # OAS Standards
        if course.get("oasStandards"):
            story.append(Paragraph("OKLAHOMA ACADEMIC STANDARDS", section_heading_style))
            for std in course["oasStandards"]:
                story.append(Paragraph(f"• {std}", bullet_style))
            story.append(Spacer(1, 0.08 * inch))

        # Grading method
        if course.get("gradingMethod"):
            story.append(Paragraph("ASSESSMENT METHOD", section_heading_style))
            story.append(Paragraph(course["gradingMethod"], body_style))

        # Mastery score
        if course.get("masteryScore") is not None:
            mastery = float(course["masteryScore"])
            pct = int(mastery * 100)
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph(
                f"<b>Mastery Confidence:</b> {pct}%",
                small_style,
            ))

    # ─ Back cover ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 1.0 * inch))
    story.append(Paragraph("NOTES FROM THE MENTOR", course_title_style))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph(
        "This student has engaged in rigorous, truth-centered learning across multiple disciplines. "
        "The evidence of mastery documented in this portfolio reflects genuine comprehension — "
        "not merely assignment completion, but deep engagement with primary sources, "
        "authentic projects, and verifiable learning outcomes. "
        "We are confident in this student\u2019s academic preparation.",
        body_style,
    ))

    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=PARA))
    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph(
        "Dear Adeline Classical Academy",
        small_style,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
```

**Checklist:**
- [ ] Create `adeline-brain/app/services/portfolio_generator.py` with `build_mastery_portfolio_pdf()` function
- [ ] Create `adeline-brain/tests/test_portfolio_generator.py` with sample data tests
- [ ] Run tests: `pytest adeline-brain/tests/test_portfolio_generator.py -v`

---

### Task 4: Transcript API Router Updates

**Goal:** Add new endpoints for official transcript, portfolio, and OSRHE progress.

**File:** `adeline-brain/app/api/transcripts.py` (update existing file)

Add these three new endpoints alongside the existing `GET /transcripts/generate/{student_id}`:

```python
# ─ Add to existing transcripts.py ───────────────────────────────────────────

from app.services.transcript_pdf import build_official_transcript_pdf
from app.services.portfolio_generator import build_mastery_portfolio_pdf

# ... existing code ...

@router.get("/official-pdf/{student_id}")
async def get_official_transcript_pdf(
    student_id: str,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Download official academic transcript as PDF.

    Filters TranscriptEntry for isApproved=True and calculates cumulative GPA.

    Returns: PDF file for download
    """
    logger.info(f"[/transcripts/official-pdf] Generating for {student_id}")

    try:
        # Fetch student and approved courses
        student = await db.query_one(
            "SELECT id, name, gradeLevel FROM User WHERE id = $1",
            (student_id,),
        )

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Fetch approved transcript entries
        entries = await db.query(
            """
            SELECT
              courseTitle, track, creditHours, gradeLetter,
              percentScore, completedAt, isApproved
            FROM TranscriptEntry
            WHERE studentId = $1 AND isApproved = true
            ORDER BY completedAt DESC
            """,
            (student_id,),
        )

        # Convert to dicts
        entries_list = [
            {
                "courseTitle": e[0],
                "track": e[1],
                "creditHours": float(e[2]),
                "gradeLetter": e[3],
                "percentScore": e[4],
                "completedAt": e[5],
                "isApproved": e[6],
            }
            for e in entries
        ]

        # Generate PDF
        pdf_bytes = build_official_transcript_pdf(
            student=dict(student),
            transcript_entries=entries_list,
        )

        filename = f"adeline-transcript-official-{student_id}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[/transcripts/official-pdf] Error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio-pdf/{student_id}")
async def get_mastery_portfolio_pdf(
    student_id: str,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Download mastery portfolio (course descriptions + evidence) as PDF.

    Shows learning outcomes, texts, projects, and standards per course.

    Returns: PDF file for download
    """
    logger.info(f"[/transcripts/portfolio-pdf] Generating for {student_id}")

    try:
        # Fetch student
        student = await db.query_one(
            "SELECT id, name, gradeLevel FROM User WHERE id = $1",
            (student_id,),
        )

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Fetch approved courses with their learning records
        entries = await db.query(
            """
            SELECT
              te.id, te.courseTitle, te.track, te.creditHours, te.gradeLetter,
              te.oasStandards, te.completedAt
            FROM TranscriptEntry te
            WHERE te.studentId = $1 AND te.isApproved = true
            ORDER BY te.completedAt DESC
            """,
            (student_id,),
        )

        portfolio_data = []
        for entry in entries:
            entry_id, title, track, hours, grade, oas_stds, completed_at = entry

            # Fetch learning records (texts, projects) for this course
            records = await db.query(
                """
                SELECT verb, objectName, durationMs, timestamp
                FROM LearningRecord
                WHERE studentId = $1 AND objectId LIKE $2
                ORDER BY timestamp DESC
                LIMIT 50
                """,
                (student_id, f"%{entry_id}%"),
            )

            # Organize as portfolio entry
            portfolio_entry = {
                "courseTitle": title,
                "track": track,
                "description": f"A comprehensive study of {title.lower()}.",
                "learningOutcomes": [
                    "Understand foundational concepts",
                    "Engage with primary sources",
                    "Complete authentic projects",
                    "Demonstrate mastery through assessment",
                ],
                "primaryTexts": [
                    {
                        "title": "Primary Source Document",
                        "author": "Various",
                        "year": 2026,
                    }
                ],
                "projects": [
                    {
                        "title": "Capstone Project",
                        "description": "Comprehensive demonstration of mastery.",
                        "completedAt": completed_at,
                    }
                ],
                "oasStandards": oas_stds or [],
                "gradingMethod": "Witness Protocol (≥0.82) + xAPI Statements + Authentic Assessment",
                "masteryScore": 0.85,  # From journal or calculate from records
            }
            portfolio_data.append(portfolio_entry)

        # Generate PDF
        pdf_bytes = build_mastery_portfolio_pdf(
            student=dict(student),
            portfolio_data=portfolio_data,
        )

        filename = f"adeline-portfolio-{student_id}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[/transcripts/portfolio-pdf] Error")
        raise HTTPException(status_code=500, detail=str(e))


class OSRHEProgress(BaseModel):
    """OSRHE 15-unit core progress."""
    english: dict  # {earned: float, required: float, percentage: float}
    labScience: dict
    math: dict
    historyCitizenship: dict
    additionalApproved: dict
    totalEarned: float
    totalRequired: float
    percentComplete: float


@router.get("/osrhe-progress/{student_id}", response_model=OSRHEProgress)
async def get_osrhe_progress(
    student_id: str,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Get OSRHE 15-unit core progress for Oklahoma college-prep tracking.

    Returns progress toward:
    - English: 4 units
    - Lab Science: 3 units
    - Math: 3 units
    - History/Citizenship: 3 units
    - Additional approved: 2 units
    """
    logger.info(f"[/transcripts/osrhe-progress] Calculating for {student_id}")

    try:
        # Fetch approved courses grouped by bucket
        buckets = await db.query(
            """
            SELECT
              c.bucket,
              SUM(c.hoursEarned) as total_earned
            FROM CreditLedgerEntry c
            WHERE c.studentId = $1
            GROUP BY c.bucket
            """,
            (student_id,),
        )

        bucket_hours = {bucket: hours for bucket, hours in buckets}

        # Map buckets to OSRHE categories
        def get_progress(bucket: str, required: float) -> dict:
            earned = float(bucket_hours.get(bucket, 0.0))
            pct = min(100.0, (earned / required * 100)) if required > 0 else 0.0
            return {
                "earned": earned,
                "required": required,
                "percentage": round(pct, 1),
            }

        english = get_progress("ENGLISH", 4.0)
        lab_sci = get_progress("LAB_SCIENCE", 3.0)
        math = get_progress("MATH", 3.0)
        hist_cit = get_progress("SOCIAL_STUDIES", 3.0)
        additional = get_progress("ELECTIVE", 2.0)  # Fallback

        total_earned = (
            english["earned"] + lab_sci["earned"] + math["earned"] +
            hist_cit["earned"] + additional["earned"]
        )
        total_required = 15.0
        pct_complete = round((total_earned / total_required * 100), 1)

        return OSRHEProgress(
            english=english,
            labScience=lab_sci,
            math=math,
            historyCitizenship=hist_cit,
            additionalApproved=additional,
            totalEarned=round(total_earned, 1),
            totalRequired=total_required,
            percentComplete=pct_complete,
        )

    except Exception as e:
        logger.exception("[/transcripts/osrhe-progress] Error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{student_id}")
async def get_approved_courses(
    student_id: str,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    List all approved courses for a student (used by dashboard).

    Returns: List of approved TranscriptEntry objects
    """
    logger.info(f"[/transcripts/courses] Fetching for {student_id}")

    try:
        entries = await db.query(
            """
            SELECT
              id, courseTitle, track, creditHours, gradeLetter,
              percentScore, completedAt, isApproved
            FROM TranscriptEntry
            WHERE studentId = $1 AND isApproved = true
            ORDER BY completedAt DESC
            """,
            (student_id,),
        )

        return [
            {
                "id": e[0],
                "courseTitle": e[1],
                "track": e[2],
                "creditHours": float(e[3]),
                "gradeLetter": e[4],
                "percentScore": e[5],
                "completedAt": e[6],
                "isApproved": e[7],
            }
            for e in entries
        ]

    except Exception as e:
        logger.exception("[/transcripts/courses] Error")
        raise HTTPException(status_code=500, detail=str(e))
```

**Checklist:**
- [ ] Update `adeline-brain/app/api/transcripts.py` with new endpoints
- [ ] Update imports: add `build_official_transcript_pdf` and `build_mastery_portfolio_pdf`
- [ ] Create `OSRHEProgress` Pydantic model
- [ ] Run API tests: `pytest adeline-brain/tests/test_api_transcripts.py -v`

---

### Task 5: Brain Client Transcript Functions (TypeScript)

**Goal:** Add type-safe REST client methods for transcript endpoints.

**File:** `adeline-ui/src/lib/brain-client.ts` (update existing)

```typescript
/**
 * Add these methods to the existing BrainClient class
 */

// ─ Transcript Models ────────────────────────────────────────────────────────

export interface TranscriptCourse {
  id: string;
  courseTitle: string;
  track: string;
  creditHours: number;
  gradeLetter: string;
  percentScore?: number;
  completedAt?: string;
  isApproved: boolean;
}

export interface OSRHEBucket {
  earned: number;
  required: number;
  percentage: number;
}

export interface OSRHEProgress {
  english: OSRHEBucket;
  labScience: OSRHEBucket;
  math: OSRHEBucket;
  historyCitizenship: OSRHEBucket;
  additionalApproved: OSRHEBucket;
  totalEarned: number;
  totalRequired: number;
  percentComplete: number;
}

// ─ BrainClient methods ──────────────────────────────────────────────────────

export class BrainClient {
  // ... existing methods ...

  /**
   * Download official academic transcript as PDF.
   * Student must be logged in.
   */
  async downloadOfficialTranscriptPDF(studentId: string): Promise<Blob> {
    const url = `${this.baseUrl}/transcripts/official-pdf/${studentId}`;
    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(
        `Failed to download transcript: ${response.statusText}`
      );
    }

    return response.blob();
  }

  /**
   * Download mastery portfolio (course descriptions) as PDF.
   */
  async downloadMasteryPortfolioPDF(studentId: string): Promise<Blob> {
    const url = `${this.baseUrl}/transcripts/portfolio-pdf/${studentId}`;
    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(
        `Failed to download portfolio: ${response.statusText}`
      );
    }

    return response.blob();
  }

  /**
   * Get OSRHE 15-unit core progress.
   * Used by OSRHEDashboard component.
   */
  async getOSRHEProgress(studentId: string): Promise<OSRHEProgress> {
    const url = `${this.baseUrl}/transcripts/osrhe-progress/${studentId}`;
    return this.fetchJSON<OSRHEProgress>(url, { method: "GET" });
  }

  /**
   * Get list of approved courses for a student.
   */
  async getApprovedCourses(studentId: string): Promise<TranscriptCourse[]> {
    const url = `${this.baseUrl}/transcripts/courses/${studentId}`;
    return this.fetchJSON<TranscriptCourse[]>(url, { method: "GET" });
  }

  /**
   * Helper: Trigger a PDF download in the browser.
   * Usage: const blob = await client.downloadOfficialTranscriptPDF(id);
   *        downloadBlob(blob, "adeline-transcript.pdf");
   */
  static downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}
```

**Checklist:**
- [ ] Update `adeline-ui/src/lib/brain-client.ts` with new methods
- [ ] Add TypeScript interfaces: `TranscriptCourse`, `OSRHEBucket`, `OSRHEProgress`
- [ ] Add helper method: `downloadBlob()`
- [ ] Run TypeScript check: `pnpm tsc --noEmit`

---

### Task 6: OSRHE Dashboard Component

**Goal:** Visual progress bars showing college-prep 15-unit requirement.

**File:** `adeline-ui/src/components/transcript/OSRHEDashboard.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import { BrainClient, OSRHEProgress } from "@/lib/brain-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface OSRHEDashboardProps {
  studentId: string;
  brainClient: BrainClient;
}

/**
 * OSRHEDashboard — Oklahoma college-prep 15-unit core tracker.
 *
 * Displays progress toward:
 * - English: 4 units (minimum)
 * - Lab Science: 3 units (minimum)
 * - Math: 3 units (minimum)
 * - History/Citizenship: 3 units (minimum)
 * - Additional Approved: 2 units (minimum)
 *
 * Each category shows a progress bar, earned/required, and percentage.
 */
export function OSRHEDashboard({
  studentId,
  brainClient,
}: OSRHEDashboardProps) {
  const [progress, setProgress] = useState<OSRHEProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadProgress() {
      try {
        setLoading(true);
        const data = await brainClient.getOSRHEProgress(studentId);
        setProgress(data);
        setError(null);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load OSRHE progress"
        );
      } finally {
        setLoading(false);
      }
    }

    loadProgress();
  }, [studentId, brainClient]);

  if (loading) {
    return <div className="text-center py-8">Loading progress...</div>;
  }

  if (error) {
    return (
      <div className="text-red-600 py-8">
        Error: {error}
      </div>
    );
  }

  if (!progress) {
    return <div className="py-8">No progress data available.</div>;
  }

  const categories = [
    { label: "English", data: progress.english, color: "bg-blue-500" },
    {
      label: "Lab Science",
      data: progress.labScience,
      color: "bg-green-500",
    },
    { label: "Mathematics", data: progress.math, color: "bg-purple-500" },
    {
      label: "History / Citizenship",
      data: progress.historyCitizenship,
      color: "bg-amber-500",
    },
    {
      label: "Additional Approved",
      data: progress.additionalApproved,
      color: "bg-indigo-500",
    },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Oklahoma College-Prep 15-Unit Core</CardTitle>
          <p className="text-sm text-gray-600">
            Progress toward state graduation requirements
          </p>
        </CardHeader>
        <CardContent className="space-y-8">
          {/* Total progress bar */}
          <div className="bg-gray-100 rounded-lg p-4">
            <div className="flex justify-between mb-2">
              <span className="font-semibold">Total Progress</span>
              <span className="text-sm font-bold">
                {progress.totalEarned.toFixed(1)} / {progress.totalRequired}{" "}
                units
              </span>
            </div>
            <ProgressBar
              percentage={progress.percentComplete}
              color="bg-gradient-to-r from-blue-500 to-green-500"
            />
            <p className="text-xs text-gray-600 mt-1">
              {progress.percentComplete.toFixed(0)}% complete
            </p>
          </div>

          {/* Category breakdown */}
          <div className="space-y-5">
            {categories.map((cat) => (
              <div key={cat.label}>
                <div className="flex justify-between items-center mb-2">
                  <label className="font-medium text-sm">{cat.label}</label>
                  <div className="text-sm">
                    <span className="font-bold">{cat.data.earned.toFixed(1)}</span>
                    <span className="text-gray-600"> / {cat.data.required}</span>
                  </div>
                </div>
                <ProgressBar
                  percentage={cat.data.percentage}
                  color={cat.color}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {cat.data.percentage.toFixed(0)}%
                </p>
              </div>
            ))}
          </div>

          {/* Status message */}
          {progress.percentComplete >= 100 ? (
            <div className="bg-green-50 border border-green-200 rounded p-4 text-sm text-green-700">
              <strong>Ready for college!</strong> Student has met the Oklahoma
              15-unit core requirement.
            </div>
          ) : (
            <div className="bg-blue-50 border border-blue-200 rounded p-4 text-sm text-blue-700">
              <strong>
                {(15 - progress.totalEarned).toFixed(1)} units remaining
              </strong>{" "}
              to complete the Oklahoma college-prep core.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * ProgressBar — reusable horizontal progress indicator.
 */
interface ProgressBarProps {
  percentage: number;
  color?: string;
}

function ProgressBar({ percentage, color = "bg-blue-500" }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, percentage));
  return (
    <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
      <div
        className={`h-full ${color} transition-all duration-300 flex items-center justify-end pr-2`}
        style={{ width: `${clamped}%` }}
      >
        {clamped > 10 && (
          <span className="text-xs font-bold text-white">
            {clamped.toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  );
}
```

**Checklist:**
- [ ] Create `adeline-ui/src/components/transcript/OSRHEDashboard.tsx`
- [ ] Create `ProgressBar` sub-component
- [ ] Add to component library/exports
- [ ] Visual test: ensure bars display correctly at 0%, 50%, 100%

---

### Task 7: Transcript Page + Sidebar Navigation

**Goal:** Add transcript page to Next.js app and link in sidebar.

**File A:** `adeline-ui/src/app/(routes)/dashboard/transcript/page.tsx`

```typescript
"use client";

import { useAuth } from "@/lib/auth-context";
import { BrainClient } from "@/lib/brain-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { OSRHEDashboard } from "@/components/transcript/OSRHEDashboard";
import { OfficialTranscript } from "@/components/transcript/OfficialTranscript";
import { MasteryPortfolio } from "@/components/transcript/MasteryPortfolio";
import { useEffect, useState } from "react";

export default function TranscriptPage() {
  const { user } = useAuth();
  const [brainClient] = useState(() => new BrainClient());
  const [activeTab, setActiveTab] = useState<
    "official" | "portfolio" | "osrhe"
  >("osrhe");

  if (!user) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Transcript</h1>
        <p className="text-gray-600 mb-8">
          View your academic record, mastery portfolio, and college-prep
          progress.
        </p>

        {/* Tab navigation */}
        <div className="flex gap-4 mb-8 border-b border-gray-200">
          <button
            onClick={() => setActiveTab("osrhe")}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "osrhe"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            College Prep (OSRHE)
          </button>
          <button
            onClick={() => setActiveTab("official")}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "official"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            Official Transcript
          </button>
          <button
            onClick={() => setActiveTab("portfolio")}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === "portfolio"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            Mastery Portfolio
          </button>
        </div>

        {/* Tab content */}
        {activeTab === "osrhe" && (
          <OSRHEDashboard
            studentId={user.id}
            brainClient={brainClient}
          />
        )}

        {activeTab === "official" && (
          <OfficialTranscript
            studentId={user.id}
            brainClient={brainClient}
          />
        )}

        {activeTab === "portfolio" && (
          <MasteryPortfolio
            studentId={user.id}
            brainClient={brainClient}
          />
        )}
      </div>
    </div>
  );
}
```

**File B:** `adeline-ui/src/components/transcript/OfficialTranscript.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import { BrainClient, TranscriptCourse } from "@/lib/brain-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface OfficialTranscriptProps {
  studentId: string;
  brainClient: BrainClient;
}

export function OfficialTranscript({
  studentId,
  brainClient,
}: OfficialTranscriptProps) {
  const [courses, setCourses] = useState<TranscriptCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCourses() {
      try {
        setLoading(true);
        const data = await brainClient.getApprovedCourses(studentId);
        setCourses(data);
        setError(null);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load transcript courses"
        );
      } finally {
        setLoading(false);
      }
    }

    loadCourses();
  }, [studentId, brainClient]);

  async function handleDownloadPDF() {
    try {
      setDownloading(true);
      const blob = await brainClient.downloadOfficialTranscriptPDF(studentId);
      BrainClient.downloadBlob(blob, `adeline-transcript-official.pdf`);
    } catch (err) {
      alert(
        `Failed to download: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setDownloading(false);
    }
  }

  if (loading) {
    return <div className="text-center py-8">Loading transcript...</div>;
  }

  if (error) {
    return (
      <div className="text-red-600 py-8">
        Error: {error}
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Official Academic Transcript</CardTitle>
          <p className="text-sm text-gray-600 mt-1">
            {courses.length} approved courses
          </p>
        </div>
        <Button
          onClick={handleDownloadPDF}
          disabled={downloading || courses.length === 0}
          className="bg-blue-600 hover:bg-blue-700"
        >
          {downloading ? "Generating PDF..." : "Download PDF"}
        </Button>
      </CardHeader>
      <CardContent>
        {courses.length === 0 ? (
          <p className="text-gray-600">No approved courses yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-300 bg-gray-50">
                  <th className="text-left px-4 py-2">Course Title</th>
                  <th className="text-left px-4 py-2">Year</th>
                  <th className="text-center px-4 py-2">Credits</th>
                  <th className="text-center px-4 py-2">Grade</th>
                </tr>
              </thead>
              <tbody>
                {courses.map((course) => (
                  <tr
                    key={course.id}
                    className="border-b border-gray-200 hover:bg-gray-50"
                  >
                    <td className="px-4 py-3">{course.courseTitle}</td>
                    <td className="px-4 py-3">
                      {course.completedAt
                        ? new Date(course.completedAt).getFullYear()
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {course.creditHours.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-center font-semibold">
                      {course.gradeLetter}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

**File C:** `adeline-ui/src/components/transcript/MasteryPortfolio.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import { BrainClient } from "@/lib/brain-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface MasteryPortfolioProps {
  studentId: string;
  brainClient: BrainClient;
}

export function MasteryPortfolio({
  studentId,
  brainClient,
}: MasteryPortfolioProps) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownloadPortfolio() {
    try {
      setDownloading(true);
      const blob = await brainClient.downloadMasteryPortfolioPDF(studentId);
      BrainClient.downloadBlob(blob, `adeline-portfolio.pdf`);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to download portfolio"
      );
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Mastery Portfolio</CardTitle>
          <p className="text-sm text-gray-600 mt-1">
            Course descriptions, learning outcomes, and evidence
          </p>
        </div>
        <Button
          onClick={handleDownloadPortfolio}
          disabled={downloading}
          className="bg-green-600 hover:bg-green-700"
        >
          {downloading ? "Generating PDF..." : "Download Portfolio"}
        </Button>
      </CardHeader>
      <CardContent>
        {error && <div className="text-red-600 mb-4">{error}</div>}
        <div className="bg-blue-50 border border-blue-200 rounded p-4 text-sm text-blue-700">
          <p>
            Your mastery portfolio is a comprehensive record of your learning
            journey. It includes course descriptions, primary texts, projects,
            and standards mastery for each class.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
```

**File D:** Update `adeline-ui/src/components/app-sidebar.tsx` (add Transcript nav)

```typescript
// In your AppSidebar component, add this nav item:

import { Users, BookOpen, FileText, BarChart3 } from "lucide-react";

// ... existing code ...

<SidebarMenu>
  {/* ... existing menu items ... */}

  <SidebarMenuSeparator />

  <SidebarMenuItem>
    <SidebarMenuButton asChild>
      <Link href="/dashboard/transcript" className="flex items-center gap-2">
        <FileText className="w-4 h-4" />
        <span>Transcript</span>
      </Link>
    </SidebarMenuButton>
  </SidebarMenuItem>

  {/* ... */}
</SidebarMenu>
```

**Checklist:**
- [ ] Create `adeline-ui/src/app/(routes)/dashboard/transcript/page.tsx`
- [ ] Create `adeline-ui/src/components/transcript/OfficialTranscript.tsx`
- [ ] Create `adeline-ui/src/components/transcript/MasteryPortfolio.tsx`
- [ ] Update `adeline-ui/src/components/app-sidebar.tsx` with Transcript nav item
- [ ] Test navigation: click "Transcript" in sidebar
- [ ] Verify page loads without errors

---

### Task 8: Integration Test & Preview

**Goal:** End-to-end test: create sample student, generate all three PDFs, verify output.

**File:** `adeline-brain/tests/test_transcript_integration.py`

```python
"""
Integration tests for transcript system.
Tests the full flow: fetch student → calculate GPA → generate PDFs.
"""

import pytest
from datetime import datetime
from app.services.gpa_calculator import calculate_gpa, GradeLetter
from app.services.transcript_pdf import build_official_transcript_pdf
from app.services.portfolio_generator import build_mastery_portfolio_pdf


class TestTranscriptIntegration:
    """End-to-end transcript generation tests."""

    def test_full_transcript_flow(self):
        """Test: student → courses → GPA → PDF."""

        # Sample student
        student = {
            "id": "student-001",
            "name": "Sarah Mitchell",
            "gradeLevel": "10",
        }

        # Sample transcript entries (approved courses)
        entries = [
            {
                "courseTitle": "Environmental Science",
                "track": "CREATION_SCIENCE",
                "creditHours": 4.0,
                "gradeLetter": "A",
                "percentScore": 92.5,
                "completedAt": "2025-11-15T00:00:00Z",
                "isApproved": True,
            },
            {
                "courseTitle": "English Language Arts",
                "track": "ENGLISH_LITERATURE",
                "creditHours": 4.0,
                "gradeLetter": "A_MINUS",
                "percentScore": 88.0,
                "completedAt": "2025-11-30T00:00:00Z",
                "isApproved": True,
            },
            {
                "courseTitle": "Applied Mathematics",
                "track": "APPLIED_MATHEMATICS",
                "creditHours": 3.0,
                "gradeLetter": "B_PLUS",
                "percentScore": 83.5,
                "completedAt": "2025-12-10T00:00:00Z",
                "isApproved": True,
            },
            {
                "courseTitle": "American & World History",
                "track": "TRUTH_HISTORY",
                "creditHours": 3.0,
                "gradeLetter": "A",
                "percentScore": 95.0,
                "completedAt": "2026-01-20T00:00:00Z",
                "isApproved": True,
            },
        ]

        # Test GPA calculation
        gpa_result = calculate_gpa(entries)
        assert gpa_result.creditsAttempted == 14.0
        assert gpa_result.creditsEarned == 14.0
        # Expected: (4*4.0 + 4*3.7 + 3*3.3 + 3*4.0) / 14 = 53.1 / 14 = 3.79
        assert gpa_result.cumulativeGPA == 3.79

        # Test official transcript PDF generation
        pdf_bytes = build_official_transcript_pdf(
            student=student,
            transcript_entries=entries,
            generated_date=datetime(2026, 4, 1),
        )

        # Verify PDF is generated and has content
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000  # PDF should be substantial
        assert b"DEAR ADELINE" in pdf_bytes or b"Sarah Mitchell" in pdf_bytes

        # Test mastery portfolio PDF generation
        portfolio_data = [
            {
                "courseTitle": entry["courseTitle"],
                "track": entry["track"],
                "description": f"An in-depth study of {entry['courseTitle'].lower()}.",
                "learningOutcomes": [
                    "Master foundational concepts",
                    "Engage with primary sources",
                    "Complete authentic projects",
                ],
                "primaryTexts": [
                    {"title": "Sample Primary Source", "author": "Various", "year": 2025},
                ],
                "projects": [
                    {
                        "title": "Capstone Project",
                        "description": "Final comprehensive demonstration of mastery.",
                        "completedAt": entry["completedAt"],
                    }
                ],
                "oasStandards": ["OK-Grade-X-Standard-Y"],
                "gradingMethod": "Witness Protocol (≥0.82) + xAPI Statements",
                "masteryScore": 0.92,
            }
            for entry in entries
        ]

        portfolio_bytes = build_mastery_portfolio_pdf(
            student=student,
            portfolio_data=portfolio_data,
            generated_date=datetime(2026, 4, 1),
        )

        assert isinstance(portfolio_bytes, bytes)
        assert len(portfolio_bytes) > 2000
        assert b"MASTERY PORTFOLIO" in portfolio_bytes or b"Sarah Mitchell" in portfolio_bytes

    def test_gpa_with_mixed_grades(self):
        """Test GPA calculation with A, B, C, and failing grades."""
        entries = [
            {
                "courseTitle": "English I",
                "creditHours": 4.0,
                "gradeLetter": "A",
            },  # 16 quality pts
            {
                "courseTitle": "Biology",
                "creditHours": 4.0,
                "gradeLetter": "B",
            },  # 12 quality pts
            {
                "courseTitle": "Algebra",
                "creditHours": 3.0,
                "gradeLetter": "C",
            },  # 6 quality pts
            {
                "courseTitle": "Failed Physics",
                "creditHours": 3.0,
                "gradeLetter": "F",
            },  # 0 quality pts
        ]

        result = calculate_gpa(entries)
        # GPA = (16 + 12 + 6) / (4 + 4 + 3) = 34 / 11 = 3.09
        assert result.cumulativeGPA == 3.09
        assert result.creditsAttempted == 14.0
        assert result.creditsEarned == 11.0  # F doesn't count

    def test_pdf_generation_no_courses(self):
        """Test PDF generation with no courses (edge case)."""
        student = {"id": "student-002", "name": "Empty Student", "gradeLevel": "9"}

        # Empty entries
        pdf_bytes = build_official_transcript_pdf(
            student=student,
            transcript_entries=[],
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Checklist:**
- [ ] Create `adeline-brain/tests/test_transcript_integration.py`
- [ ] Run integration tests: `pytest adeline-brain/tests/test_transcript_integration.py -v`
- [ ] All tests pass
- [ ] Manually test in browser: navigate to /dashboard/transcript
- [ ] Download official transcript PDF and verify content
- [ ] Download portfolio PDF and verify content
- [ ] Test OSRHE dashboard with sample data
- [ ] Verify sidebar "Transcript" navigation works

---

## Self-Review Checklist

### Architecture & Design
- [ ] GPA calculation is pure (no DB calls, testable, reusable)
- [ ] PDF generation uses reportlab consistently (colors, fonts, layout)
- [ ] TRACK_CREDIT_MAP external names used everywhere (never internal names on PDFs)
- [ ] OSRHE 15-unit buckets map correctly to CreditBucket enum
- [ ] All endpoints return proper HTTP status codes (404 for missing student, 500 for errors)
- [ ] TypeScript types align with Python models (TranscriptCourse, OSRHEProgress)

### Code Quality
- [ ] All new Python functions have docstrings explaining args, return, and rules
- [ ] All TypeScript components are properly typed (no `any`)
- [ ] No hardcoded student IDs or test data in production code
- [ ] Error handling: fetch failures show user-friendly messages
- [ ] Logging at INFO level for user actions, ERROR for exceptions

### Database Queries
- [ ] Queries filter by `isApproved=true` (not showing unapproved courses)
- [ ] Queries use index-friendly WHERE clauses (studentId, completedAt)
- [ ] No N+1 queries (single fetch for student, single fetch for courses)
- [ ] Decimal precision: creditHours and GPA to 1-2 decimal places

### UI/UX
- [ ] Transcript page has three clear tabs (OSRHE, Official, Portfolio)
- [ ] Download buttons have loading states and error messages
- [ ] Progress bars cap at 100% (no overflow)
- [ ] OSRHE dashboard shows "Ready for college!" when complete
- [ ] Sidebar "Transcript" link is visible and clickable

### Testing
- [ ] Unit tests for GPA calculator (100% coverage of GRADE_POINTS)
- [ ] Unit tests for PDF generation (check for expected text/content)
- [ ] Integration test: student → courses → GPA → PDFs
- [ ] Edge cases covered: no courses, mixed grades, PASS/FAIL grades
- [ ] All tests pass locally before committing

### Verification
- [ ] Official transcript PDF includes:
  - Student name, ID, date
  - Course table with title, year, credits, grade
  - GPA calculation (cumulative, total attempted/earned)
  - Grading scale legend
  - Registrar seal
- [ ] Mastery portfolio PDF includes:
  - Course descriptions
  - Learning outcomes
  - Primary texts and projects
  - OAS standards
  - Assessment method
- [ ] OSRHE dashboard shows:
  - Total progress bar
  - 5 category breakdowns (English, Lab Science, Math, History, Additional)
  - Earned/required per category
  - Percentage complete
  - Status message (on track / ready / incomplete)

### Documentation
- [ ] This plan is saved to `/docs/superpowers/plans/2026-04-01-transcript-system.md`
- [ ] Code comments explain non-obvious logic (e.g., why PASS/FAIL not in GPA)
- [ ] README (if needed) documents new API endpoints

---

## Post-Implementation Notes

**Future enhancements:**
1. Transcript PDF signature: allow parent/admin to digitally sign before download
2. Transcript sharing: secure shareable link for colleges
3. Portfolio customization: student chooses which courses/projects to highlight
4. Weighted GPA: track major vs. elective credits separately
5. Predicted GPA: show student what their GPA will be with different grades

**Known limitations:**
- OSRHE dashboard assumes all CreditBucket entries have been set correctly in Plan C
- Portfolio data (texts, projects, outcomes) must be manually entered or auto-generated from LearningRecords
- PDF generation is synchronous (large portfolios may take a few seconds)

---

**Status:** Ready for subagent-driven development or executing-plans skill. Each task is independent and can be worked in parallel after Task 1 (GPA calculator) completes.

