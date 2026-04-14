"""
The Witness Protocol
"A matter must be established by the testimony of two or three witnesses." — Deuteronomy 19:15

Enforces similarity thresholds for truth claims.
Witness Protocol applies ONLY to TRUTH_HISTORY — the one track where every block
must be backed by a verified primary source.

All other tracks bypass Witness entirely (threshold = 0.0), so they never produce
ARCHIVE_SILENT verdicts or forced Research Missions.

Threshold is configurable via environment variable:
  WITNESS_HISTORY_THRESHOLD — for TRUTH_HISTORY only (default: 0.82)
"""
import os
from typing import Optional
from app.schemas.api_models import Evidence, EvidenceVerdict, WitnessCitation
import logging

logger = logging.getLogger(__name__)

_HISTORY_THRESHOLD = float(os.getenv("WITNESS_HISTORY_THRESHOLD", "0.82"))


def get_witness_threshold(track: str) -> float:
    """
    Witness Protocol is STRICTLY for TRUTH_HISTORY only.
    - TRUTH_HISTORY: High bar (0.82) for primary-source grounding.
    - Everything else: Disabled (0.0) — never blocks, never triggers ARCHIVE_SILENT.

    Threshold is overridable via env var WITNESS_HISTORY_THRESHOLD.
    """
    if track == "TRUTH_HISTORY":
        return _HISTORY_THRESHOLD
    return 0.0


def evaluate_evidence(
    source_id: str,
    source_title: str,
    similarity_score: float,
    chunk: str,
    track: str = "TRUTH_HISTORY",
    source_url: str = "",
    citation_author: str = "",
    citation_year: Optional[int] = None,
    citation_archive_name: str = "",
) -> Evidence:
    """
    Evaluate a retrieved chunk against the Witness Protocol threshold.
    Only runs the cosine check for TRUTH_HISTORY — all other tracks are
    immediately VERIFIED without threshold enforcement.
    Returns an Evidence object with verdict, citation, and full metadata.
    """
    if track != "TRUTH_HISTORY":
        logger.info(f"[WITNESS] Track={track} | Witness bypassed (non-history) — '{source_title}' auto-VERIFIED")
        verdict = EvidenceVerdict.VERIFIED
    else:
        threshold = get_witness_threshold(track)
        if similarity_score >= threshold:
            verdict = EvidenceVerdict.VERIFIED
            logger.info(
                f"[WITNESS] VERIFIED — '{source_title}' "
                f"Track={track} | Threshold={threshold} | Score={similarity_score:.3f}"
            )
        else:
            verdict = EvidenceVerdict.ARCHIVE_SILENT
            logger.warning(
                f"[WITNESS] ARCHIVE_SILENT — '{source_title}' "
                f"Track={track} | Threshold={threshold} | Score={similarity_score:.3f}"
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
