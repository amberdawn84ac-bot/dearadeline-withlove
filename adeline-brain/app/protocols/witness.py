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


def evaluate_evidence(
    source_id: str,
    source_title: str,
    similarity_score: float,
    chunk: str,
    source_url: str = "",
    citation_author: str = "",
    citation_year: Optional[int] = None,
    citation_archive_name: str = "",
) -> Evidence:
    """
    Evaluate a retrieved chunk against the Witness Protocol threshold.
    Returns an Evidence object with verdict, citation, and full metadata.
    """
    if similarity_score >= WITNESS_THRESHOLD:
        verdict = EvidenceVerdict.VERIFIED
        logger.info(f"[WITNESS] VERIFIED — '{source_title}' score={similarity_score:.3f}")
    else:
        verdict = EvidenceVerdict.ARCHIVE_SILENT
        logger.warning(
            f"[WITNESS] ARCHIVE_SILENT — '{source_title}' score={similarity_score:.3f} "
            f"(below threshold {WITNESS_THRESHOLD})"
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
