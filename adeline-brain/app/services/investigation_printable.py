"""Printable learner dossier renderer for a canonical family investigation."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import reportlab

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _plain(value: object) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    text = re.sub(r"[#*_`>$]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def build_investigation_pdf(*, title: str, topic: str, grade_level: str, blocks: list[dict]) -> bytes:
    """Render adapted canonical blocks as a polished, standards-free field dossier."""
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=.68*inch, leftMargin=.68*inch,
                            topMargin=.62*inch, bottomMargin=.62*inch, title=title)
    font_dir = Path(reportlab.__file__).parent / "fonts"
    pdfmetrics.registerFont(TTFont("AdelineSans", str(font_dir / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("AdelineSansBold", str(font_dir / "VeraBd.ttf")))
    pdfmetrics.registerFont(TTFont("AdelineSerifBold", str(font_dir / "VeraBd.ttf")))
    styles = getSampleStyleSheet()
    green, orange, cream = colors.HexColor("#2F4731"), colors.HexColor("#BD6809"), colors.HexColor("#FDF6E9")
    title_style = ParagraphStyle("DA Title", parent=styles["Title"], fontName="AdelineSerifBold", fontSize=27,
                                 leading=30, textColor=green, alignment=TA_CENTER, spaceAfter=16)
    eyebrow = ParagraphStyle("DA Eyebrow", parent=styles["Normal"], fontName="AdelineSansBold", fontSize=8,
                              textColor=orange, alignment=TA_CENTER, spaceAfter=10)
    heading = ParagraphStyle("DA Heading", parent=styles["Heading2"], fontName="AdelineSerifBold", fontSize=18,
                              leading=22, textColor=green, spaceAfter=8)
    body = ParagraphStyle("DA Body", parent=styles["BodyText"], fontName="AdelineSans", fontSize=10.5,
                           leading=16, textColor=colors.HexColor("#263828"), spaceAfter=9)
    note = ParagraphStyle("DA Note", parent=body, fontName="AdelineSans", textColor=colors.HexColor("#566858"))

    story: list = [Paragraph("DEAR ADELINE FAMILY FIELD DOSSIER", eyebrow), Paragraph(_plain(title), title_style)]
    launch = Table([[Paragraph("<b>Investigator:</b> ______________________________", body),
                     Paragraph(f"<b>Level:</b> {_plain(grade_level)}", body)]], colWidths=[4.8*inch, 1.5*inch])
    launch.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), cream), ("BOX", (0,0), (-1,-1), 1, orange),
                                ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 10),
                                ("RIGHTPADDING", (0,0), (-1,-1), 10), ("TOPPADDING", (0,0), (-1,-1), 9)]))
    story += [launch, Spacer(1, 16), Paragraph(f"Follow the evidence, make or test something real, and preserve what you discover about {_plain(topic)}.", note)]

    learner_blocks = [b for b in blocks if not b.get("is_silenced") and b.get("block_type") != "RESOURCE_COLLECTION"]
    for index, block in enumerate(learner_blocks, 1):
        stage = _plain(block.get("experience_stage") or "INVESTIGATE")
        block_title = _plain(block.get("title") or f"Field step {index}")
        content = _plain(block.get("content"))
        if not content:
            continue
        section = [Paragraph(f"{stage} · FIELD STEP {index}", eyebrow), Paragraph(block_title, heading), Paragraph(content, body)]
        if stage in {"ACTION", "CREATION", "DEMONSTRATION", "REFLECTION"}:
            lines = Table([[""] for _ in range(5)], colWidths=[6.65*inch], rowHeights=[.34*inch]*5)
            lines.setStyle(TableStyle([("LINEBELOW", (0,0), (-1,-1), .45, colors.HexColor("#BFB39E"))]))
            section += [Spacer(1, 5), lines]
        story += [Spacer(1, 16), KeepTogether(section)]
        if index < len(learner_blocks) and index % 2 == 0:
            story.append(PageBreak())

    story += [PageBreak(), Paragraph("MY INVESTIGATION RECORD", eyebrow), Paragraph("What I can now show", title_style),
              Paragraph("Use words, a drawing, measurements, calculations, a photo reference, or a description of what you made. Explain what your evidence shows and what you would change next time.", body)]
    record = Table([[Paragraph("My claim or discovery", heading)], [""], [Paragraph("My evidence", heading)], [""],
                    [Paragraph("What I would revise or investigate next", heading)], [""]],
                   colWidths=[6.65*inch], rowHeights=[.35*inch, 1.35*inch, .35*inch, 1.35*inch, .45*inch, 1.15*inch])
    record.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 1, green), ("INNERGRID", (0,0), (-1,-1), .4, colors.HexColor("#D9CFBC")),
                                ("BACKGROUND", (0,0), (0,0), cream), ("BACKGROUND", (0,2), (0,2), cream), ("BACKGROUND", (0,4), (0,4), cream),
                                ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 9)]))
    story.append(record)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFillColor(green)
        canvas.setFont("AdelineSans", 8)
        canvas.drawString(.68*inch, .34*inch, "Dear Adeline · Family Investigation")
        canvas.drawRightString(7.82*inch, .34*inch, f"Field page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
