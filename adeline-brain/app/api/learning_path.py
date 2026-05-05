"""
Learning Path API — /learning-path

Returns concept node state map for the Learning Path UI visualisation.

GET /learning-path/{student_id}/nodes
    Returns every Concept node the student's enrolled tracks, with:
      - state: "mastered" | "available" | "locked"
      - mastery_score (0-1 float or null)
      - prerequisite_ids (list[str])

GET /learning-path/{student_id}/nodes?track=TRUTH_HISTORY
    Same, filtered to a single track.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.connections.knowledge_graph import get_concept_graph_for_track, TRACKS_METADATA
from app.connections.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/learning-path", tags=["learning-path"])


# ── Response models ───────────────────────────────────────────────────────────

class ConceptNode(BaseModel):
    id: str
    title: str
    description: str
    track: str
    difficulty: str
    grade_band: str
    standard_code: str
    prerequisite_ids: list[str]
    state: str          # "mastered" | "available" | "locked"
    mastery_score: Optional[float] = None
    track_color: str


class LearningPathResponse(BaseModel):
    student_id: str
    nodes: list[ConceptNode]
    edges: list[dict]   # [{"from": id, "to": id}] prerequisite pairs
    mastered_count: int
    available_count: int
    locked_count: int


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_student_mastery(student_id: str) -> dict[str, float]:
    """Return {concept_id: score} for all concepts the student has mastered."""
    try:
        rows = await neo4j_client.run(
            """
            MATCH (st:Student {id: $student_id})-[m:MASTERED]->(c:Concept)
            RETURN c.id AS concept_id, m.score AS score
            """,
            {"student_id": student_id},
        )
        return {row["concept_id"]: float(row["score"]) for row in rows}
    except Exception as e:
        logger.warning(f"[LearningPath] Could not fetch mastery for {student_id}: {e}")
        return {}


def _compute_state(
    concept_id: str,
    prereq_ids: list[str],
    mastery_map: dict[str, float],
    mastery_threshold: float = 0.7,
) -> tuple[str, Optional[float]]:
    """
    Returns (state, mastery_score).
    mastered  — student has MASTERED edge with score >= threshold
    available — all prerequisites mastered, but concept itself not yet
    locked    — at least one prerequisite not yet mastered
    """
    score = mastery_map.get(concept_id)
    if score is not None and score >= mastery_threshold:
        return "mastered", round(score, 3)

    # All prerequisites must be mastered for the concept to be available
    for prereq_id in prereq_ids:
        prereq_score = mastery_map.get(prereq_id)
        if prereq_score is None or prereq_score < mastery_threshold:
            return "locked", round(score, 3) if score else None

    return "available", round(score, 3) if score else None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{student_id}/nodes", response_model=LearningPathResponse)
async def get_learning_path_nodes(
    student_id: str,
    track: Optional[str] = Query(None, description="Filter to a single track name"),
):
    """
    Return all concept nodes with computed state (mastered/available/locked)
    for a given student. Optionally filtered to one track.

    Falls back gracefully if Neo4j is unavailable — returns empty nodes list
    with appropriate warning rather than 500.
    """
    tracks_to_query = [track] if track else list(TRACKS_METADATA.keys())

    # Fetch mastery map once (all tracks)
    mastery_map = await _get_student_mastery(student_id)

    all_nodes: list[ConceptNode] = []
    all_edges: list[dict] = []
    seen_edges: set[tuple[str, str]] = set()

    for track_name in tracks_to_query:
        if track_name not in TRACKS_METADATA:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown track: {track_name}. Valid tracks: {list(TRACKS_METADATA.keys())}",
            )

        track_color = TRACKS_METADATA[track_name]["color"]

        try:
            concept_rows = await get_concept_graph_for_track(track_name)
        except Exception as e:
            logger.warning(f"[LearningPath] Neo4j query failed for track {track_name}: {e}")
            concept_rows = []

        for row in concept_rows:
            concept_id = row.get("id") or row.get("concept_id", "")
            if not concept_id:
                continue

            prereq_ids: list[str] = [p for p in (row.get("prerequisite_ids") or []) if p]
            state, mastery_score = _compute_state(concept_id, prereq_ids, mastery_map)

            all_nodes.append(ConceptNode(
                id=concept_id,
                title=row.get("name") or row.get("title", "Untitled"),
                description=row.get("description", ""),
                track=track_name,
                difficulty=row.get("difficulty", "intermediate"),
                grade_band=row.get("grade_band", ""),
                standard_code=row.get("standard_code", ""),
                prerequisite_ids=prereq_ids,
                state=state,
                mastery_score=mastery_score,
                track_color=track_color,
            ))

            # Emit prerequisite edges (deduplicated)
            for prereq_id in prereq_ids:
                edge_key = (concept_id, prereq_id)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    all_edges.append({"from": concept_id, "to": prereq_id})

    mastered_count  = sum(1 for n in all_nodes if n.state == "mastered")
    available_count = sum(1 for n in all_nodes if n.state == "available")
    locked_count    = sum(1 for n in all_nodes if n.state == "locked")

    return LearningPathResponse(
        student_id=student_id,
        nodes=all_nodes,
        edges=all_edges,
        mastered_count=mastered_count,
        available_count=available_count,
        locked_count=locked_count,
    )
