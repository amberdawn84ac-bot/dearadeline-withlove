"""
Official Transcript PDF Generator — CEEB-compliant academic record.
"""
import io
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

from app.services.gpa_calculator import calculate_gpa, GradeLetter, format_gpa, GRADE_POINTS

INK    = colors.HexColor("#2C2318")
PARA   = colors.HexColor("#9A3F4A")
ACCENT = colors.HexColor("#BD6809")


def build_official_transcript_pdf(
    student: dict,
    transcript_entries: list[dict],
    school_name: str = "Dear Adeline Classical Academy",
    school_address: str = "Oklahoma",
    generated_date: Optional[datetime] = None,
) -> bytes:
    generated_date = generated_date or datetime.now()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(buf, pagesize=LETTER,
        leftMargin=1.0*inch, rightMargin=1.0*inch,
        topMargin=1.0*inch, bottomMargin=0.75*inch)

    story = []

    title_style = ParagraphStyle("Title", fontName="Times-Bold", fontSize=16,
        textColor=INK, spaceAfter=2, alignment=1)
    sub_title_style = ParagraphStyle("SubTitle", fontName="Times-Roman", fontSize=11,
        textColor=INK, spaceAfter=1, alignment=1)
    section_style = ParagraphStyle("Section", fontName="Times-Bold", fontSize=11,
        textColor=PARA, spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle("Body", fontName="Times-Roman", fontSize=10,
        textColor=INK, spaceAfter=4, leading=12)
    small_style = ParagraphStyle("Small", fontName="Times-Roman", fontSize=9,
        textColor=INK, spaceAfter=2, leading=10)
    italic_style = ParagraphStyle("Italic", fontName="Times-Italic", fontSize=9,
        textColor=INK, spaceAfter=2, leading=10)

    # Header
    story.append(Paragraph(school_name, title_style))
    story.append(Paragraph(school_address, sub_title_style))
    story.append(Spacer(1, 0.15*inch))
    story.append(HRFlowable(width="100%", thickness=2, color=PARA))
    story.append(Spacer(1, 0.15*inch))

    # Student info
    student_info = [
        ["Student Name:", student.get("name", "")],
        ["Student ID:", student.get("id", "")[:8]],
        ["Grade Level:", student.get("gradeLevel", "")],
        ["Generated:", generated_date.strftime("%B %d, %Y")],
    ]
    info_table = Table(student_info, colWidths=[1.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (0,-1), "RIGHT"), ("ALIGN", (1,0), (1,-1), "LEFT"),
        ("FONTNAME", (0,0), (0,-1), "Times-Bold"), ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TEXTCOLOR", (0,0), (-1,-1), INK),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.2*inch))

    # Filter approved
    approved = [e for e in transcript_entries if e.get("isApproved", True)]
    if not approved:
        story.append(Paragraph("No approved courses to display.", body_style))
        doc.build(story)
        buf.seek(0)
        return buf.read()

    # Course table
    story.append(Paragraph("COURSE RECORD", section_style))
    rows = [[
        Paragraph("<b>Course Title</b>", body_style),
        Paragraph("<b>Year</b>", body_style),
        Paragraph("<b>Credits</b>", body_style),
        Paragraph("<b>Grade</b>", body_style),
        Paragraph("<b>Points</b>", body_style),
    ]]

    for entry in approved:
        title = entry.get("courseTitle", "Untitled")
        completed = entry.get("completedAt")
        if isinstance(completed, str):
            try:
                completed = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                completed = None
        year_str = completed.strftime("%Y") if completed else "—"
        credits = float(entry.get("creditHours", 0.0))
        grade_letter = entry.get("gradeLetter", "")

        try:
            grade_enum = GradeLetter[grade_letter] if isinstance(grade_letter, str) else grade_letter
            pts = GRADE_POINTS.get(grade_enum, 0.0)
        except (KeyError, AttributeError):
            pts = 0.0

        qp_str = f"{credits * pts:.1f}" if pts > 0 else "—"
        rows.append([
            Paragraph(title, small_style), Paragraph(year_str, small_style),
            Paragraph(f"{credits:.1f}", small_style), Paragraph(grade_letter, small_style),
            Paragraph(qp_str, small_style),
        ])

    course_table = Table(rows, colWidths=[3.0*inch, 0.8*inch, 0.9*inch, 0.7*inch, 0.8*inch])
    course_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Times-Bold"),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F0D9B0")),
        ("ALIGN", (2,1), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E3C07A")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#FDF8F0")]),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    story.append(course_table)
    story.append(Spacer(1, 0.15*inch))

    # GPA
    gpa = calculate_gpa(approved)
    gpa_info = [
        ["Total Credits Attempted:", f"{gpa.creditsAttempted:.1f}"],
        ["Total Credits Earned:", f"{gpa.creditsEarned:.1f}"],
        ["Cumulative GPA:", format_gpa(gpa.cumulativeGPA)],
    ]
    gpa_table = Table(gpa_info, colWidths=[2.5*inch, 1.5*inch])
    gpa_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (0,-1), "RIGHT"), ("ALIGN", (1,0), (1,-1), "CENTER"),
        ("FONTNAME", (0,0), (0,-1), "Times-Bold"),
        ("FONTNAME", (1,-1), (1,-1), "Times-Bold"),
        ("FONTSIZE", (0,-1), (1,-1), 11), ("FONTSIZE", (0,0), (0,-2), 10),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#F0D9B0")),
    ]))
    story.append(gpa_table)
    story.append(Spacer(1, 0.2*inch))

    # Grading scale
    story.append(Paragraph("GRADING SCALE", section_style))
    scale = [
        ["Grade", "Scale", "Grade", "Scale", "Grade", "Scale"],
        ["A+", "4.0", "B-", "2.7", "D", "1.0"],
        ["A", "4.0", "C+", "2.3", "D-", "0.7"],
        ["A-", "3.7", "C", "2.0", "F", "0.0"],
        ["B+", "3.3", "C-", "1.7", "PASS", "—"],
        ["B", "3.0", "D+", "1.3", "FAIL", "—"],
    ]
    scale_table = Table(scale, colWidths=[1.0*inch, 1.0*inch]*3)
    scale_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Times-Bold"),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F0D9B0")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E3C07A")),
    ]))
    story.append(scale_table)
    story.append(Spacer(1, 0.2*inch))

    # Registrar seal
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 0.08*inch))
    story.append(Paragraph("REGISTRAR'S CERTIFICATION",
        ParagraphStyle("Seal", fontName="Times-Bold", fontSize=10, textColor=ACCENT)))
    story.append(Paragraph(
        "This is an official academic record. All courses reflect verified learning "
        "through the Witness Protocol. This transcript may be submitted for college admissions.",
        italic_style))
    story.append(Spacer(1, 0.4*inch))

    sig_table = Table(
        [["_____________________", "", "_____________________"],
         ["Registrar Signature", "", "Date"]],
        colWidths=[2.0*inch, 1.0*inch, 2.0*inch])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"), ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    story.append(sig_table)

    doc.build(story)
    buf.seek(0)
    return buf.read()
