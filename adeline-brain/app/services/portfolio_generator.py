"""
Mastery Portfolio PDF Generator — student accomplishment record with reflection.
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

INK    = colors.HexColor("#2C2318")
PARA   = colors.HexColor("#9A3F4A")
ACCENT = colors.HexColor("#BD6809")


def build_mastery_portfolio_pdf(
    student: dict,
    portfolio_items: list[dict],
    school_name: str = "Dear Adeline Classical Academy",
    school_address: str = "Oklahoma",
    generated_date: Optional[datetime] = None,
) -> bytes:
    """
    Generate a mastery portfolio PDF showcasing student accomplishments.

    Args:
        student: Dict with keys: name, id, gradeLevel
        portfolio_items: List of dicts with keys:
            - title (str): What the student made/accomplished
            - category (str): Track name (e.g., "Creation Science", "Creative Economy")
            - description (str): Student's reflection or narrative
            - dateCompleted (str or datetime): When it was completed
            - proofUrl (str, optional): Link to evidence (portfolio site, photo, etc.)
            - impact (str, optional): Why this matters (real-world application)
        school_name: School name for header
        school_address: School location for header
        generated_date: PDF generation timestamp

    Returns:
        bytes: PDF file content
    """
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
    category_style = ParagraphStyle("Category", fontName="Times-Italic", fontSize=9,
        textColor=PARA, spaceAfter=2)

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

    # Portfolio intro
    story.append(Paragraph("MASTERY PORTFOLIO", section_style))
    story.append(Paragraph(
        "The following accomplishments represent real learning through making, building, "
        "growing, publishing, and selling. Each entry reflects verified evidence of mastery.",
        italic_style))
    story.append(Spacer(1, 0.15*inch))

    # Filter portfolio items
    if not portfolio_items:
        story.append(Paragraph("No portfolio items to display.", body_style))
        doc.build(story)
        buf.seek(0)
        return buf.read()

    # Portfolio items
    for idx, item in enumerate(portfolio_items, 1):
        # Item header with title and category
        title_text = item.get("title", "Untitled")
        category_text = item.get("category", "")

        story.append(Paragraph(f"{idx}. {title_text}", body_style))
        if category_text:
            story.append(Paragraph(f"Track: {category_text}", category_style))

        # Metadata row
        completed = item.get("dateCompleted")
        if isinstance(completed, str):
            try:
                completed = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                completed = None
        date_str = completed.strftime("%B %d, %Y") if completed else "—"

        metadata = [
            ["Date Completed:", date_str],
        ]
        if item.get("proofUrl"):
            metadata.append(["Evidence:", item.get("proofUrl", "")])

        if metadata:
            meta_table = Table(metadata, colWidths=[1.5*inch, 3.5*inch])
            meta_table.setStyle(TableStyle([
                ("ALIGN", (0,0), (0,-1), "RIGHT"), ("ALIGN", (1,0), (1,-1), "LEFT"),
                ("FONTNAME", (0,0), (0,-1), "Times-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9),
                ("TEXTCOLOR", (0,0), (-1,-1), INK),
                ("TOPPADDING", (0,0), (-1,-1), 2), ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ]))
            story.append(meta_table)

        # Description
        description = item.get("description", "")
        if description:
            story.append(Paragraph("<b>Student Reflection:</b>", small_style))
            story.append(Paragraph(description, small_style))

        # Impact
        impact = item.get("impact", "")
        if impact:
            story.append(Paragraph("<b>Real-World Impact:</b>", small_style))
            story.append(Paragraph(impact, small_style))

        story.append(Spacer(1, 0.1*inch))

    story.append(Spacer(1, 0.15*inch))

    # Portfolio seal
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 0.08*inch))
    story.append(Paragraph("PORTFOLIO CERTIFICATION",
        ParagraphStyle("Seal", fontName="Times-Bold", fontSize=10, textColor=ACCENT)))
    story.append(Paragraph(
        "This portfolio represents verified accomplishments in real-world learning. "
        "Each entry documents what the student has made, built, grown, published, or sold—"
        "not merely completed. This portfolio is submitted as evidence of mastery.",
        italic_style))
    story.append(Spacer(1, 0.4*inch))

    sig_table = Table(
        [["_____________________", "", "_____________________"],
         ["Parent/Guardian", "", "Date"]],
        colWidths=[2.0*inch, 1.0*inch, 2.0*inch])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"), ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))
    story.append(sig_table)

    doc.build(story)
    buf.seek(0)
    return buf.read()
