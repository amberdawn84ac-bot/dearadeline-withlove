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

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.knowledge_graph import get_concept_graph_for_track, TRACKS_METADATA
from app.connections.neo4j_client import neo4j_client
from app.connections.postgres import get_db_session
from app.services.standards_mapper import StandardsMapper

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


# ── Gap Detection ("Gap Filler Loop") ───────────────────────────────────────

class GapStandard(BaseModel):
    """A learning gap with reason for priority."""
    standard_id: str
    reason: str


class LearningGapsResponse(BaseModel):
    """Response identifying student's priority learning gaps."""
    student_id: str
    priority_subject: str
    saturation: float
    gap_standards: list[GapStandard]
    suggested_daily_bread: str


@router.get("/{student_id}/gaps", response_model=LearningGapsResponse)
async def identify_learning_gaps(
    student_id: str,
    use_prerequisite_chain: bool = Query(True, description="Use Neo4j prerequisite chains for smarter gaps"),
    db: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Identify learning gaps using prerequisite chain logic.
    
    **Wire 1: Prerequisite Chain (Neo4j FEEDS_INTO)**
    
    When use_prerequisite_chain=True:
    - Finds the student's most recently mastered standard
    - Queries Neo4j for FEEDS_INTO relationships
    - Returns the next logical standard (not just random unmastered)
    - Example: "Multiplication" → "Division" → "Fractions"
    
    Called by: Daily Bread generator for personalized prompts
    """
    # Security check
    if student_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot view other student's gaps")
    
    mapper = StandardsMapper(db)
    
    try:
        # Get overall progress first
        report = await mapper.get_student_standards_progress(
            student_id=student_id,
            pg_session=db,
        )
        
        if not report.by_subject:
            return LearningGapsResponse(
                student_id=student_id,
                priority_subject="MATH",
                saturation=0.0,
                gap_standards=[],
                suggested_daily_bread="Start with foundational math concepts.",
            )
        
        # Find lowest saturation subject
        lowest_subject = min(
            report.by_subject.values(),
            key=lambda s: s.saturation_percentage,
        )
        
        gap_standards: list[GapStandard] = []
        
        if use_prerequisite_chain:
            # **Wire 1: Use Neo4j prerequisite chains**
            # Find the most recently mastered standard in the lowest subject
            # Query Neo4j for what it feeds into (the next logical step)
            
            # First, find a recently mastered standard to build from
            # In production, this would query the actual most recent
            masteries = await db.execute(
                text("""
                    SELECT "standardId", proficiency, "lastAssessedAt"
                    FROM "StandardMastery"
                    WHERE "studentId" = :student_id
                      AND subject = :subject
                      AND proficiency IN ('UNDERSTANDING', 'EXTENDING')
                    ORDER BY "lastAssessedAt" DESC
                    LIMIT 1
                """),
                {"student_id": student_id, "subject": lowest_subject.subject},
            )
            recent = masteries.mappings().first()
            
            if recent:
                last_standard_id = recent["standardId"]
                
                # Query Neo4j for next logical standards
                next_standards = await mapper.get_next_logical_standards(
                    standard_id=last_standard_id,
                    student_id=student_id,
                )
                
                if next_standards:
                    # Use the prerequisite chain
                    for std in next_standards[:3]:
                        gap_standards.append(GapStandard(
                            standard_id=std.code,
                            reason=f"Follows from your mastery of {last_standard_id}",
                        ))
                else:
                    # No chain found, use generic gaps
                    for std_id in lowest_subject.gap_standards[:3]:
                        gap_standards.append(GapStandard(
                            standard_id=std_id,
                            reason=f"Prerequisite for {lowest_subject.subject} mastery",
                        ))
            else:
                # No recent mastery, suggest foundational standards
                for std_id in lowest_subject.gap_standards[:3]:
                    gap_standards.append(GapStandard(
                        standard_id=std_id,
                        reason=f"Foundation for {lowest_subject.subject}",
                    ))
        else:
            # Simple gap detection without prerequisite chain
            for std_id in lowest_subject.gap_standards[:5]:
                gap_standards.append(GapStandard(
                    standard_id=std_id,
                    reason=f"Prerequisite for {lowest_subject.subject} mastery",
                ))
        
        # Generate Daily Bread suggestion based on gaps
        if gap_standards:
            next_standard = gap_standards[0].standard_id
            daily_bread = (
                f"Let's continue your {lowest_subject.subject} journey. "
                f"Next up: {next_standard.split('.')[-1]}. "
                f"This builds directly on what you mastered. Ready?"
            )
        else:
            daily_bread = (
                f"Great progress in {lowest_subject.subject}! "
                f"Time to explore advanced applications."
            )
        
        return LearningGapsResponse(
            student_id=student_id,
            priority_subject=lowest_subject.subject,
            saturation=lowest_subject.saturation_percentage,
            gap_standards=gap_standards,
            suggested_daily_bread=daily_bread,
        )
    except Exception as e:
        logger.error(f"[LearningPath] Gap detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to identify gaps: {str(e)}")
