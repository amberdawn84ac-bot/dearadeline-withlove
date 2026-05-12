"""
GraphRAG Query Tool — structured access to the Neo4j knowledge graph for agents.

Gives agents structured access to the Neo4j knowledge graph to:
  - Get ZPD concept recommendations per student/track (BKT-aware)
  - Walk prerequisite chains (multi-hop reasoning)
  - Find cross-track thematic connections

Used by: orchestrator agents, learning_plan, and lessons.py when building lesson context.

ZPD selection hierarchy:
  1. BKT-aware (get_zpd_candidates_with_bkt) — uses per-concept pL from SpacedRepetitionCard
     + compute_priority(prereq_readiness, mastery_gap, leverage) from zpd_engine.py
  2. Graph-only fallback (get_zpd_candidates) — binary MASTERED-edge gate from Neo4j
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

from app.connections.knowledge_graph import (
    get_zpd_candidates,
    get_zpd_candidates_with_bkt,
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
    # BKT fields — populated when using bkt-aware path
    priority:        float = 0.0
    current_mastery: float = 0.0
    prereq_readiness: float = 1.0


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

    Uses BKT-aware selection (SpacedRepetitionCard.masteryLevel + compute_priority)
    when data is available, falling back to graph-only selection when not.

    BKT path returns candidates with real priority scores from:
      compute_priority(prereq_readiness, mastery_gap, leverage)
    so the highest-leverage, most-ready concepts surface first.
    """
    from app.algorithms.bkt_tracker import get_mastery_map_with_timestamps, build_mastery_snapshots

    # ── Try BKT-aware path first ───────────────────────────────────────────────
    try:
        mastery_map_ts = await get_mastery_map_with_timestamps(student_id, track)
        # Need concept graph rows to build snapshots — get_zpd_candidates_with_bkt handles this
        # We need concept rows to build snapshots: fetch them inline
        from app.connections.knowledge_graph import get_concept_graph_for_track
        concept_rows = await get_concept_graph_for_track(track)

        if concept_rows:
            mastery_snapshots = build_mastery_snapshots(concept_rows, mastery_map_ts)
            zpd_concepts = await get_zpd_candidates_with_bkt(track, mastery_snapshots, limit)

            if zpd_concepts:
                candidates = [
                    ZPDCandidate(
                        concept_id=z.concept_id,
                        title=z.name,
                        description=z.description,
                        track=z.track,
                        difficulty="",
                        standard_code=z.standard_code or "",
                        grade_band=z.grade_band or "",
                        dependent_count=0,
                        prereq_count=0,
                        priority=z.priority,
                        current_mastery=z.current_mastery,
                        prereq_readiness=z.prerequisite_readiness,
                    )
                    for z in zpd_concepts
                ]
                logger.info(
                    f"[GraphQuery] BKT ZPD candidates for student={student_id[:8]}, "
                    f"track={track}: {len(candidates)} found "
                    f"(top priority={candidates[0].priority:.3f})"
                )
                return candidates
    except Exception as e:
        logger.warning(f"[GraphQuery] BKT ZPD path failed, using graph fallback: {e}")

    # ── Graph-only fallback (binary MASTERED edges) ──────────────────────────────────
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
            priority=0.5,  # Neutral priority — no BKT data available
        )
        for r in raw
    ]
    logger.info(
        f"[GraphQuery] Graph-only ZPD candidates for student={student_id[:8]}, "
        f"track={track}: {len(candidates)} found"
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
