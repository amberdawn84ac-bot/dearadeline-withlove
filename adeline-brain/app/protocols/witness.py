"""
The Witness Protocol
"A matter must be established by the testimony of two or three witnesses." — Deuteronomy 19:15

Enforces similarity thresholds for truth claims.

Tracks with Witness enforcement:
  TRUTH_HISTORY         — every block must be backed by a verified primary source (0.82 default)
  JUSTICE_CHANGEMAKING  — same primary-source requirement; lobbying records, civil rights docs,
                          legislative history (threshold configurable independently via env var)

All other tracks bypass Witness entirely (threshold = 0.0), so they never produce
ARCHIVE_SILENT verdicts or forced Research Missions.

Thresholds are configurable via environment variables:
  WITNESS_HISTORY_THRESHOLD — for TRUTH_HISTORY (default: 0.82)
  WITNESS_JUSTICE_THRESHOLD — for JUSTICE_CHANGEMAKING (default: same as TRUTH_HISTORY)
"""
import os
from typing import Optional
from app.schemas.api_models import Evidence, EvidenceVerdict, WitnessCitation
import logging

logger = logging.getLogger(__name__)

_HISTORY_THRESHOLD = float(os.getenv("WITNESS_HISTORY_THRESHOLD", "0.82"))
_JUSTICE_THRESHOLD = float(os.getenv("WITNESS_JUSTICE_THRESHOLD", str(_HISTORY_THRESHOLD)))

_WITNESS_TRACKS = {"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"}


def get_witness_threshold(track: str) -> float:
    """
    Returns the cosine-similarity threshold for the given track.

    - TRUTH_HISTORY:        High bar for primary-source grounding (0.82 default).
    - JUSTICE_CHANGEMAKING: Same primary-source requirement — lobbying records, civil rights
                            documents, legislative history must be verified before display.
                            Independently configurable via WITNESS_JUSTICE_THRESHOLD.
    - Everything else:      Disabled (0.0) — never blocks, never triggers ARCHIVE_SILENT.
    """
    if track == "TRUTH_HISTORY":
        return _HISTORY_THRESHOLD
    if track == "JUSTICE_CHANGEMAKING":
        return _JUSTICE_THRESHOLD
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
    Enforces the cosine check for TRUTH_HISTORY and JUSTICE_CHANGEMAKING.
    All other tracks are immediately VERIFIED without threshold enforcement.
    Returns an Evidence object with verdict, citation, and full metadata.
    """
    if track not in _WITNESS_TRACKS:
        logger.info(f"[WITNESS] Track={track} | Witness bypassed — '{source_title}' auto-VERIFIED")
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
