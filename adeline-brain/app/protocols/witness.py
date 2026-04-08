"""
The Witness Protocol
"A matter must be established by the testimony of two or three witnesses." — Deuteronomy 19:15

Enforces the 0.82 similarity threshold for all historical truth claims.
If evidence does not meet the threshold, ARCHIVE_SILENT is returned
and no content is generated — a Research Mission is assigned instead.
"""
from typing import Optional
from app.schemas.api_models import Evidence, EvidenceVerdict, WitnessCitation, TRUTH_THRESHOLD as WITNESS_THRESHOLD
import logging

logger = logging.getLogger(__name__)


def get_witness_threshold(track: str) -> float:
    """
    Return similarity threshold based on track requirements.
    
    - TRUTH_HISTORY, JUSTICE_CHANGEMAKING: 0.82 (strict - primary sources only)
    - DISCIPLESHIP, ENGLISH_LITERATURE: 0.65 (permissive - scripture/worldview)
    - All others: 0.75 (medium - general content)
    """
    STRICT_TRACKS = {"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"}
    PERMISSIVE_TRACKS = {"DISCIPLESHIP", "ENGLISH_LITERATURE"}
    
    if track in STRICT_TRACKS:
        return 0.82  # Historical truth claims require verified primary sources
    elif track in PERMISSIVE_TRACKS:
        return 0.65  # Scripture/worldview content is more permissive
    else:
        return 0.75  # Default for science, homesteading, math, etc.


def evaluate_evidence(
    source_id: str,
    source_title: str,
    similarity_score: float,
    chunk: str,
    track: str = "TRUTH_HISTORY",  # Default to strictest threshold
    source_url: str = "",
    citation_author: str = "",
    citation_year: Optional[int] = None,
    citation_archive_name: str = "",
) -> Evidence:
    """
    Evaluate a retrieved chunk against the Witness Protocol threshold.
    Uses track-aware thresholds for different content types.
    Returns an Evidence object with verdict, citation, and full metadata.
    """
    threshold = get_witness_threshold(track)
    
    if similarity_score >= threshold:
        verdict = EvidenceVerdict.VERIFIED
        logger.info(f"[WITNESS] VERIFIED — '{source_title}' score={similarity_score:.3f} (threshold={threshold} for {track})")
    else:
        verdict = EvidenceVerdict.ARCHIVE_SILENT
        logger.warning(
            f"[WITNESS] ARCHIVE_SILENT — '{source_title}' score={similarity_score:.3f} "
            f"(below threshold {threshold} for {track})"
        )

    return Evidence(
        source_id=source_id,
        source_title=source_title,
        source_url=source_url,
        witness_citation=WitnessCitation(
            author=citation_author,
            year=citation_year,
            archive_name=citation_archive_name,
        ),
        similarity_score=similarity_score,
        verdict=verdict,
        chunk=chunk,
    )


def all_evidence_verified(evidence_list: list[Evidence]) -> bool:
    return all(e.verdict == EvidenceVerdict.VERIFIED for e in evidence_list)


def build_research_mission_block(topic: str, failed_sources: list[str]) -> dict:
    sources_text = "\n".join(f"- {s}" for s in failed_sources) if failed_sources else "- Primary sources TBD"
    return {
        "block_type": "RESEARCH_MISSION",
        "content": (
            f"Adeline doesn't have enough verified sources to teach about '{topic}' right now.\n\n"
            f"**Your Research Mission:**\n"
            f"Investigate this topic using primary sources. Look for:\n"
            f"{sources_text}\n\n"
            f"Bring what you find back to Adeline, and she'll help you evaluate it."
        ),
        "is_silenced": False,
    }
