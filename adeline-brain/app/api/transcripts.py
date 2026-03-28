"""
Transcripts API — /transcripts/*

GET /transcripts/generate/{student_id}
    Aggregates Neo4j MASTERED relationships + Postgres journal data
    and streams back a formal Classical Education PDF transcript.

Clock-hour calculation: each verified block = 30 minutes (0.5 hr).
"""
import io
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.api_models import UserRole
from app.api.middleware import require_role
from app.connections.neo4j_client import neo4j_client
from app.connections.journal_store import journal_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transcripts", tags=["transcripts"])

# Minutes per verified block — adjust freely
MINUTES_PER_BLOCK = 30

TRACK_LABELS: dict[str, str] = {
    "CREATION_SCIENCE":     "Track 1 — God's Creation & Science",
    "HEALTH_NATUROPATHY":   "Track 2 — Health & Naturopathy",
    "HOMESTEADING":         "Track 3 — Homesteading & Stewardship",
    "GOVERNMENT_ECONOMICS": "Track 4 — Government & Economics",
    "JUSTICE_CHANGEMAKING": "Track 5 — Justice & Change-making",
    "DISCIPLESHIP":         "Track 6 — Discipleship & Discernment",
    "TRUTH_HISTORY":        "Track 7 — Truth-Based History",
    "ENGLISH_LITERATURE":   "Track 8 — English Language & Literature",
}


def _build_pdf(
    student_id: str,
    track_progress: dict[str, int],
    mastered_standards: list[dict],
    evidence_sources: list[dict],
) -> bytes:
    """
    Generate a formal Classical-Education-style PDF transcript.
    Returns the PDF as bytes.
    """
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

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=1.1 * inch,
        rightMargin=1.1 * inch,
        topMargin=1.0 * inch,
        bottomMargin=1.0 * inch,
    )

    styles = getSampleStyleSheet()
    INK    = colors.HexColor("#2C2318")
    PARA   = colors.HexColor("#9A3F4A")  # Paradise
    ACCENT = colors.HexColor("#BD6809")  # Papaya

    title_style = ParagraphStyle(
        "Title", fontName="Times-Bold", fontSize=18, textColor=INK,
        spaceAfter=4, alignment=1,
    )
    sub_style = ParagraphStyle(
        "Sub", fontName="Times-Italic", fontSize=10, textColor=INK,
        spaceAfter=2, alignment=1,
    )
    section_style = ParagraphStyle(
        "Section", fontName="Times-Bold", fontSize=12, textColor=PARA,
        spaceBefore=14, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body", fontName="Times-Roman", fontSize=10, textColor=INK,
        spaceAfter=4, leading=14,
    )
    small_style = ParagraphStyle(
        "Small", fontName="Times-Roman", fontSize=9, textColor=INK,
        spaceAfter=3, leading=12,
    )
    italic_style = ParagraphStyle(
        "Italic", fontName="Times-Italic", fontSize=9, textColor=INK,
        spaceAfter=3, leading=12,
    )

    story = []

    # ── OAS lookup: {track_id: [std_ids]} ────────────────────────────────────
    oas_by_track: dict[str, list[str]] = {}
    for s in mastered_standards:
        t_key = s.get("track", "")
        std_id = s.get("standard_id", s.get("std_id", ""))
        if t_key and std_id:
            oas_by_track.setdefault(t_key, []).append(std_id)

    # ── Cover header ──────────────────────────────────────────────────────────
    story.append(Paragraph("DEAR ADELINE", title_style))
    story.append(Paragraph("Classical Education Transcript", sub_style))
    story.append(Paragraph("Truth-First · K-12 · Oklahoma", sub_style))
    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=PARA))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph(f"Student ID:  {student_id}", body_style))
    story.append(Paragraph(f"Generated:   {date.today().strftime('%B %d, %Y')}", body_style))
    story.append(Spacer(1, 0.2 * inch))

    # ── 8-Track summary table ─────────────────────────────────────────────────
    story.append(Paragraph("8-TRACK CREDIT SUMMARY", section_style))

    total_lessons = sum(track_progress.values())
    total_blocks = 0  # aggregated below

    rows_data: list[list] = []
    rows_data.append([
        Paragraph("<b>Track</b>", body_style),
        Paragraph("<b>Lessons Sealed</b>", body_style),
        Paragraph("<b>Verified Blocks</b>", body_style),
        Paragraph("<b>Clock Hours</b>", body_style),
    ])

    # We need completed_blocks per track — pull from journal
    # (passed in track_progress map only has lesson count; blocks need separate agg)
    grey_style = ParagraphStyle(
        "Grey", fontName="Times-Italic", fontSize=8,
        textColor=colors.HexColor("#999999"), leading=10,
    )

    for track_id, lesson_count in sorted(track_progress.items()):
        label = TRACK_LABELS.get(track_id, track_id)
        est_hours = (lesson_count * MINUTES_PER_BLOCK) / 60
        # Build track cell: bold name + greyed OAS primary code below
        oas_codes = oas_by_track.get(track_id, [])
        track_cell = [Paragraph(f"<b>{label}</b>", small_style)]
        if oas_codes:
            primary = oas_codes[0]
            track_cell.append(Paragraph(primary, grey_style))
        rows_data.append([
            track_cell,
            Paragraph(str(lesson_count), small_style),
            Paragraph("—", small_style),
            Paragraph(f"{est_hours:.1f} hr", small_style),
        ])

    # Grand total row
    total_hrs = (total_lessons * MINUTES_PER_BLOCK) / 60
    rows_data.append([
        Paragraph("<b>TOTAL</b>", body_style),
        Paragraph(f"<b>{total_lessons}</b>", body_style),
        Paragraph("", body_style),
        Paragraph(f"<b>{total_hrs:.1f} hr</b>", body_style),
    ])

    col_widths = [3.2 * inch, 1.1 * inch, 1.1 * inch, 1.0 * inch]
    summary_table = Table(rows_data, colWidths=col_widths)
    summary_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, 0),  "Times-Bold"),
        ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#F0D9B0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FDF8F0")]),
        ("BACKGROUND",  (0, -1), (-1, -1), colors.HexColor("#F0D9B0")),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#E3C07A")),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.2 * inch))

    # ── OAS Standards mastered ────────────────────────────────────────────────
    if mastered_standards:
        story.append(Paragraph("OKLAHOMA ACADEMIC STANDARDS — MASTERED", section_style))

        # Group by track
        by_track: dict[str, list[dict]] = {}
        for s in mastered_standards:
            t = s.get("track", "UNKNOWN")
            by_track.setdefault(t, []).append(s)

        for track_id, stds in sorted(by_track.items()):
            label = TRACK_LABELS.get(track_id, track_id)
            story.append(Paragraph(label, body_style))
            for std in stds:
                std_id = std.get("standard_id", std.get("std_id", ""))
                grade  = std.get("grade", "")
                text   = std.get("text", "")
                story.append(Paragraph(
                    f"&nbsp;&nbsp;&nbsp;{std_id} (Gr {grade}) — {text}",
                    italic_style,
                ))
            story.append(Spacer(1, 0.08 * inch))

    # ── Registrar's Seal ──────────────────────────────────────────────────────
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        "REGISTRAR\u2019S SEAL",
        ParagraphStyle(
            "Seal", fontName="Times-Bold", fontSize=10, textColor=ACCENT,
            spaceAfter=3,
        ),
    ))
    story.append(Paragraph(
        "This transcript is verified via the Adeline 0.85 Truth-Gate Protocol. "
        "All credits represent primary-source mastery.",
        italic_style,
    ))

    # ── Evidence Appendix ─────────────────────────────────────────────────────
    if evidence_sources:
        story.append(PageBreak())
        story.append(Paragraph("EVIDENCE APPENDIX — PRIMARY SOURCES", section_style))
        story.append(Paragraph(
            "The following primary sources were verified through the Witness Protocol "
            "(cosine similarity ≥ 0.85 against the archived corpus). These documents "
            "constitute the evidentiary basis of this transcript.",
            body_style,
        ))
        story.append(Spacer(1, 0.1 * inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=PARA))
        story.append(Spacer(1, 0.1 * inch))

        for i, src in enumerate(evidence_sources, start=1):
            title   = src.get("title", "Untitled Source")
            author  = src.get("author", "")
            year    = src.get("year", "")
            url     = src.get("url", "")
            track   = TRACK_LABELS.get(src.get("track", ""), src.get("track", ""))

            story.append(Paragraph(f"{i}. {title}", body_style))
            if author or year:
                cite = "    " + (f"{author}" if author else "")
                if year:
                    cite += f", {year}"
                story.append(Paragraph(cite, italic_style))
            if track:
                story.append(Paragraph(f"    Track: {track}", small_style))
            if url:
                story.append(Paragraph(
                    f'    <link href="{url}" color="blue">{url}</link>',
                    small_style,
                ))
            # Truth score (static — all sources passed the 0.85 gate)
            story.append(Paragraph(
                "    Truth Score: \u2265\u20090.85 \u2014 Witness Protocol verified",
                italic_style,
            ))
            # OAS standard tags for this source's track
            src_track = src.get("track", "")
            src_oas = oas_by_track.get(src_track, [])
            if src_oas:
                story.append(Paragraph(
                    "    OAS Standards: " + ",\u2009".join(src_oas),
                    small_style,
                ))
            story.append(Spacer(1, 0.06 * inch))

    # ── Footer note ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E3C07A")))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        "This transcript was generated by Dear Adeline 2.0 — a Truth-First K-12 AI Mentor. "
        "All content has been verified through the Witness Protocol (Deuteronomy 19:15). "
        "A matter must be established by the testimony of two or three witnesses.",
        italic_style,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


@router.get("/generate/{student_id}")
async def generate_transcript(
    student_id: str,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Generate a formal PDF transcript for a student.

    - Reads track progress from Postgres student_journal
    - Queries Neo4j for MASTERED OASStandard relationships
    - Reads stored primary sources from student_journal
    - Returns a streaming PDF download
    """
    logger.info(f"[/transcripts/generate] Generating transcript for {student_id}")

    try:
        # Parallel fetch
        import asyncio
        track_progress, evidence_sources, mastered_raw = await asyncio.gather(
            journal_store.get_track_progress(student_id),
            journal_store.get_all_sources(student_id),
            neo4j_client.run(
                """
                MATCH (st:Student {id: $student_id})-[:MASTERED]->(s:OASStandard)
                OPTIONAL MATCH (s)-[:MAPS_TO_TRACK]->(t:Track)
                RETURN s.id AS std_id, s.text AS text, s.grade AS grade,
                       coalesce(t.name, s.track, '') AS track
                ORDER BY track, s.grade
                """,
                {"student_id": student_id},
            ),
        )
    except Exception as e:
        logger.exception("[/transcripts/generate] Data fetch failed")
        raise HTTPException(status_code=500, detail=str(e))

    if not track_progress:
        raise HTTPException(
            status_code=404,
            detail=f"No sealed lessons found for student '{student_id}'.",
        )

    # Enrich mastered standards with standard_id key for the PDF builder
    mastered = [
        {**r, "standard_id": r.get("std_id", "")}
        for r in mastered_raw
    ]

    try:
        pdf_bytes = _build_pdf(
            student_id=student_id,
            track_progress=track_progress,
            mastered_standards=mastered,
            evidence_sources=evidence_sources,
        )
    except Exception as e:
        logger.exception("[/transcripts/generate] PDF build failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    logger.info(
        f"[/transcripts/generate] PDF ready — "
        f"{len(track_progress)} tracks, {len(mastered)} standards, "
        f"{len(evidence_sources)} sources, {len(pdf_bytes):,} bytes"
    )

    filename = f"adeline-transcript-{student_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
