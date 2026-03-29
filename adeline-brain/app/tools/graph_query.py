"""
GraphRAG Query Tool — LangGraph-compatible tool for agent graph queries.

Gives agents structured access to the Neo4j knowledge graph to:
  - Get ZPD concept recommendations per student/track
  - Walk prerequisite chains (multi-hop reasoning)
  - Find cross-track thematic connections

Used by: orchestrator agents when building lesson context
"""
from __future__ import annotations
import logging
from dataclasses import dataclass

from app.connections.knowledge_graph import (
    get_zpd_candidates,
    get_prerequisite_chain,
    get_cross_track_concepts,
)

logger = logging.getLogger(__name__)


@dataclass
class ZPDCandidate:
    concept_id:      str
    title:           str
    description:     str
    track:           str
    difficulty:      str
    standard_code:   str
    grade_band:      str
    dependent_count: int
    prereq_count:    int


@dataclass
class PrerequisiteConcept:
    concept_id: str
    title:      str
    track:      str
    difficulty: str
    distance:   int


@dataclass
class CrossTrackConcept:
    concept_id:  str
    title:       str
    track:       str
    description: str
    track_theme: str


async def tool_get_zpd_candidates(
    student_id: str, track: str, limit: int = 5
) -> list[ZPDCandidate]:
    """
    Return the top ZPD concept candidates for a student on a given track.

    Filters to concepts where:
    - Student has not yet mastered (score >= 0.7)
    - All prerequisites ARE mastered

    Ordered by dependent_count DESC (highest leverage first — mastering these
    unlocks the most subsequent concepts).
    """
    raw = await get_zpd_candidates(student_id, track, limit)
    candidates = [
        ZPDCandidate(
            concept_id=r.get("concept_id", ""),
            title=r.get("title", ""),
            description=r.get("description", ""),
            track=r.get("track", ""),
            difficulty=r.get("difficulty", ""),
            standard_code=r.get("standard_code", ""),
            grade_band=r.get("grade_band", ""),
            dependent_count=r.get("dependent_count", 0),
            prereq_count=r.get("prereq_count", 0),
        )
        for r in raw
    ]
    logger.info(
        f"[GraphQuery] ZPD candidates for student={student_id}, track={track}: "
        f"{len(candidates)} found"
    )
    return candidates


async def tool_get_prerequisite_chain(
    concept_id: str, depth: int = 3
) -> list[PrerequisiteConcept]:
    """
    Return the prerequisite chain for a concept (up to `depth` hops).

    Enables Adeline to explain: 'Before we study soil pH, you need to
    understand composting — and before composting, you need garden basics.'
    """
    raw = await get_prerequisite_chain(concept_id, depth)
    chain = [
        PrerequisiteConcept(
            concept_id=r.get("concept_id", ""),
            title=r.get("title", ""),
            track=r.get("track", ""),
            difficulty=r.get("difficulty", ""),
            distance=r.get("distance", 1),
        )
        for r in raw
    ]
    logger.info(
        f"[GraphQuery] Prerequisite chain for concept={concept_id}: "
        f"{len(chain)} hops found"
    )
    return chain


async def tool_get_cross_track_context(
    track: str, topic_keywords: list[str], limit: int = 4
) -> list[CrossTrackConcept]:
    """
    Find concepts on OTHER tracks that share keywords with this lesson topic.

    Powers multi-hop reasoning examples:
    - HOMESTEADING lesson on soil pH → CREATION_SCIENCE concepts on soil biology
    - TRUTH_HISTORY lesson on Dawes Act → HOMESTEADING concepts on land stewardship
    - JUSTICE_CHANGEMAKING lesson on Trail of Tears → TRUTH_HISTORY source analysis

    Returns related concepts from other tracks for cross-disciplinary context.
    """
    raw = await get_cross_track_concepts(track, topic_keywords, limit)
    concepts = [
        CrossTrackConcept(
            concept_id=r.get("concept_id", ""),
            title=r.get("title", ""),
            track=r.get("track", ""),
            description=r.get("description", ""),
            track_theme=r.get("track_theme", ""),
        )
        for r in raw
    ]
    logger.info(
        f"[GraphQuery] Cross-track concepts for track={track}, "
        f"keywords={topic_keywords}: {len(concepts)} found"
    )
    return concepts


def format_zpd_for_agent_prompt(candidates: list[ZPDCandidate]) -> str:
    """Format ZPD candidates for injection into an agent's lesson generation prompt."""
    if not candidates:
        return "No ZPD concept candidates found for this student on this track."
    lines = ["Student's Zone of Proximal Development (top concepts ready to learn next):"]
    for i, c in enumerate(candidates, 1):
        lines.append(
            f"{i}. **{c.title}** [{c.track}] "
            f"(Difficulty: {c.difficulty}, Grade Band: {c.grade_band}, "
            f"Standard: {c.standard_code or 'N/A'}, "
            f"Unlocks {c.dependent_count} further concept(s))"
        )
    return "\n".join(lines)


def format_prerequisites_for_agent_prompt(
    concept_title: str, chain: list[PrerequisiteConcept]
) -> str:
    """Format prerequisite chain for injection into an agent's scaffolding prompt."""
    if not chain:
        return f"No prerequisites found for '{concept_title}'."
    lines = [f"Prerequisites for '{concept_title}' (closest first):"]
    for p in chain:
        indent = "  " * (p.distance - 1) + "→ "
        lines.append(f"{indent}{p.title} [{p.track}] (Difficulty: {p.difficulty})")
    return "\n".join(lines)
