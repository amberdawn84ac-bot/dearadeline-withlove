"""
LangGraph Multi-Agent Orchestrator
Routes lesson requests to the appropriate specialist agent based on Track.
Enforces the Witness Protocol before any content reaches the student.

Researcher Upgrade: when Hippocampus returns ARCHIVE_SILENT, the orchestrator
calls SearchWitnesses (Tavily → scrape → cosine) before falling back to a
RESEARCH_MISSION block. If a verified source is found, the lesson continues
with a PRIMARY_SOURCE block from the auto-found archive.
"""
import uuid
import logging
from typing import TypedDict, Literal

from app.schemas.api_models import (
    LessonRequest, LessonResponse, LessonBlockResponse,
    Track, BlockType, EvidenceVerdict,
)
from app.protocols.witness import evaluate_evidence, build_research_mission_block
from app.connections.pgvector_client import hippocampus
from app.connections.neo4j_client import neo4j_client
from app.tools.researcher import search_witnesses

logger = logging.getLogger(__name__)

TRUTH_HISTORY_TRACK = Track.TRUTH_HISTORY.value


# ── Agent State ───────────────────────────────────────────────────────────────

class AdelineState(TypedDict):
    request: LessonRequest
    lesson_id: str
    query_embedding: list[float]
    blocks: list[dict]
    oas_standards: list[dict]
    has_research_missions: bool
    researcher_activated: bool


# ── Neo4j graph-link (multi-hop) ──────────────────────────────────────────────

async def _fetch_graph_context(track: str) -> list[dict]:
    """
    Multi-hop graph context for a lesson.

    Returns two categories of OAS standards, each tagged with source_type:
      'primary'     — standards on the requested track (direct curriculum match)
      'cross_track' — standards on connected tracks via CROSS_TRACK_LINK

    The cross-track entries include 'bridge_standard_text' explaining WHY the
    connection exists, and 'connected_track' naming the other track.
    This powers Adeline's ability to say:
      "This connects to [Track] because [bridge standard says...]"
    """
    results = []

    # 1. Primary standards for the requested track
    try:
        primary = await neo4j_client.run(
            """
            MATCH (s:OASStandard)-[:MAPS_TO_TRACK]->(t:Track {name: $track})
            RETURN s.id AS standard_id,
                   s.standard_text AS text,
                   s.grade AS grade,
                   coalesce(s.lesson_hook, '') AS lesson_hook,
                   $track AS connected_track,
                   'primary' AS source_type,
                   '' AS bridge_standard_text
            ORDER BY s.grade
            LIMIT 4
            """,
            {"track": track},
        )
        results.extend(primary)
    except Exception as e:
        logger.warning(f"[Neo4j] primary standards query failed for track={track}: {e}")

    # 2. Cross-track connections via CROSS_TRACK_LINK (1 hop)
    try:
        cross = await neo4j_client.get_cross_track_context(track, limit=4)
        for row in cross:
            results.append({
                "standard_id":         row.get("standard_id", ""),
                "text":                row.get("text", ""),
                "grade":               row.get("grade", 0),
                "lesson_hook":         row.get("lesson_hook", ""),
                "connected_track":     row.get("connected_track", ""),
                "source_type":         "cross_track",
                "bridge_standard_text": row.get("bridge_standard_text", ""),
            })
    except Exception as e:
        logger.warning(f"[Neo4j] cross-track query failed for track={track}: {e}")

    return results


# ── Historian Agent (TRUTH_HISTORY) ──────────────────────────────────────────

async def historian_agent(state: AdelineState) -> AdelineState:
    """
    Truth-Based History specialist.
    PRIMARY_SOURCE blocks when VERIFIED.
    On ARCHIVE_SILENT: tries SearchWitnesses before falling back to RESEARCH_MISSION.
    Most strict application of the Witness Protocol.
    """
    request = state["request"]
    blocks: list[dict] = []

    raw_results = await hippocampus.similarity_search(
        query_embedding=state["query_embedding"],
        track=TRUTH_HISTORY_TRACK,
        top_k=3,
    )

    for result in raw_results:
        evidence = evaluate_evidence(
            source_id=result["id"],
            source_title=result["source_title"],
            source_url=result.get("source_url", ""),
            citation_author=result.get("citation_author", ""),
            citation_year=result.get("citation_year"),
            citation_archive_name=result.get("citation_archive_name", ""),
            similarity_score=float(result["similarity_score"]),
            chunk=result["chunk"],
        )

        if evidence.verdict == EvidenceVerdict.ARCHIVE_SILENT:
            logger.info(
                f"[Orchestrator] ARCHIVE_SILENT on '{result['source_title']}' — "
                "activating Researcher..."
            )
            witness = await search_witnesses(
                topic=request.topic,
                track=TRUTH_HISTORY_TRACK,
                query_embedding=state["query_embedding"],
                lesson_id=state["lesson_id"],
            )

            if witness:
                state["researcher_activated"] = True
                content = witness.evidence.chunk
                blocks.append({
                    "block_type": BlockType.PRIMARY_SOURCE.value,
                    "content": (
                        f"*[Adeline searched the archives and found:]*\n\n{content}"
                    ),
                    "evidence": [witness.evidence.model_dump()],
                    "is_silenced": False,
                    "homestead_content": (
                        _homestead_adapt(content) if request.is_homestead else None
                    ),
                })
            else:
                mission = build_research_mission_block(
                    request.topic, [result["source_title"]]
                )
                blocks.append({
                    **mission,
                    "block_type": BlockType.RESEARCH_MISSION.value,
                    "evidence": [evidence.model_dump()],
                })
                state["has_research_missions"] = True
        else:
            content = result["chunk"]
            blocks.append({
                "block_type": BlockType.PRIMARY_SOURCE.value,
                "content": content,
                "evidence": [evidence.model_dump()],
                "is_silenced": False,
                "homestead_content": (
                    _homestead_adapt(content) if request.is_homestead else None
                ),
            })

    # If Hippocampus returned nothing at all, try the researcher
    if not blocks:
        logger.info(
            "[Orchestrator] Empty Hippocampus result — activating Researcher..."
        )
        witness = await search_witnesses(
            topic=request.topic,
            track=TRUTH_HISTORY_TRACK,
            query_embedding=state["query_embedding"],
            lesson_id=state["lesson_id"],
        )
        if witness:
            state["researcher_activated"] = True
            blocks.append({
                "block_type": BlockType.PRIMARY_SOURCE.value,
                "content": (
                    f"*[Adeline searched the archives and found:]*\n\n"
                    f"{witness.evidence.chunk}"
                ),
                "evidence": [witness.evidence.model_dump()],
                "is_silenced": False,
                "homestead_content": None,
            })
        else:
            mission = build_research_mission_block(request.topic, [])
            blocks.append({
                **mission,
                "block_type": BlockType.RESEARCH_MISSION.value,
                "evidence": [],
            })
            state["has_research_missions"] = True

    state["blocks"] = blocks
    return state


# ── General Mentor Agent ──────────────────────────────────────────────────────

async def general_mentor_agent(state: AdelineState) -> AdelineState:
    """
    General mentor for non-History tracks.
    Witness Protocol still applies.
    On ARCHIVE_SILENT: tries SearchWitnesses before falling back to RESEARCH_MISSION.
    """
    request = state["request"]
    blocks: list[dict] = []

    raw_results = await hippocampus.similarity_search(
        query_embedding=state["query_embedding"],
        track=request.track.value,
        top_k=3,
    )

    for result in raw_results:
        evidence = evaluate_evidence(
            source_id=result["id"],
            source_title=result["source_title"],
            source_url=result.get("source_url", ""),
            citation_author=result.get("citation_author", ""),
            citation_year=result.get("citation_year"),
            citation_archive_name=result.get("citation_archive_name", ""),
            similarity_score=float(result["similarity_score"]),
            chunk=result["chunk"],
        )

        if evidence.verdict == EvidenceVerdict.VERIFIED:
            content = result["chunk"]
            blocks.append({
                "block_type": BlockType.PRIMARY_SOURCE.value,
                "content": content,
                "evidence": [evidence.model_dump()],
                "is_silenced": False,
                "homestead_content": (
                    _homestead_adapt(content) if request.is_homestead else None
                ),
            })

        elif evidence.verdict == EvidenceVerdict.ARCHIVE_SILENT:
            logger.info(
                f"[Orchestrator] ARCHIVE_SILENT on '{result['source_title']}' — "
                "activating Researcher..."
            )
            witness = await search_witnesses(
                topic=request.topic,
                track=request.track.value,
                query_embedding=state["query_embedding"],
                lesson_id=state["lesson_id"],
            )

            if witness:
                state["researcher_activated"] = True
                content = witness.evidence.chunk
                blocks.append({
                    "block_type": BlockType.PRIMARY_SOURCE.value,
                    "content": (
                        f"*[Adeline searched the archives and found:]*\n\n{content}"
                    ),
                    "evidence": [witness.evidence.model_dump()],
                    "is_silenced": False,
                    "homestead_content": (
                        _homestead_adapt(content) if request.is_homestead else None
                    ),
                })
            else:
                mission = build_research_mission_block(
                    request.topic, [result["source_title"]]
                )
                blocks.append({
                    **mission,
                    "block_type": BlockType.RESEARCH_MISSION.value,
                    "evidence": [evidence.model_dump()],
                })
                state["has_research_missions"] = True

    if not blocks:
        logger.info(
            "[Orchestrator] Empty Hippocampus result — activating Researcher..."
        )
        witness = await search_witnesses(
            topic=request.topic,
            track=request.track.value,
            query_embedding=state["query_embedding"],
            lesson_id=state["lesson_id"],
        )
        if witness:
            state["researcher_activated"] = True
            blocks.append({
                "block_type": BlockType.PRIMARY_SOURCE.value,
                "content": (
                    f"*[Adeline searched the archives and found:]*\n\n"
                    f"{witness.evidence.chunk}"
                ),
                "evidence": [witness.evidence.model_dump()],
                "is_silenced": False,
                "homestead_content": None,
            })
        else:
            mission = build_research_mission_block(request.topic, [])
            blocks.append({
                **mission,
                "block_type": BlockType.RESEARCH_MISSION.value,
                "evidence": [],
            })
            state["has_research_missions"] = True

    state["blocks"] = blocks
    return state


def _homestead_adapt(content: str) -> str:
    return (
        f"[Homestead Lens] {content[:300]}...\n\n"
        "*How does this connect to caring for your land and family?*"
    )


# ── Router ────────────────────────────────────────────────────────────────────

def _route(state: AdelineState) -> Literal["historian", "general_mentor"]:
    if state["request"].track == Track.TRUTH_HISTORY:
        return "historian"
    return "general_mentor"


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def run_orchestrator(
    request: LessonRequest, query_embedding: list[float]
) -> LessonResponse:
    """
    Routes the request to the correct specialist agent, graph-links to
    OAS Standards via Neo4j, and returns a structured LessonResponse.

    When Hippocampus lacks verified sources (ARCHIVE_SILENT), the Researcher
    tool automatically searches archive.org, gutenberg.org, and archives.gov
    before falling back to a student-facing RESEARCH_MISSION.
    """
    lesson_id = str(uuid.uuid4())

    state: AdelineState = {
        "request": request,
        "lesson_id": lesson_id,
        "query_embedding": query_embedding,
        "blocks": [],
        "oas_standards": [],
        "has_research_missions": False,
        "researcher_activated": False,
    }

    route = _route(state)
    logger.info(f"[Orchestrator] Routing to: {route} | topic='{request.topic}'")

    if route == "historian":
        state = await historian_agent(state)
    else:
        state = await general_mentor_agent(state)

    state["oas_standards"] = await _fetch_graph_context(request.track.value)
    primary_count = sum(1 for s in state["oas_standards"] if s.get("source_type") == "primary")
    cross_count   = sum(1 for s in state["oas_standards"] if s.get("source_type") == "cross_track")
    logger.info(
        f"[Orchestrator] Graph context: {primary_count} primary + {cross_count} cross-track | "
        f"blocks: {len(state['blocks'])} | "
        f"research_missions: {state['has_research_missions']} | "
        f"researcher_activated: {state['researcher_activated']}"
    )

    blocks = [LessonBlockResponse(**b) for b in state["blocks"]]

    return LessonResponse(
        lesson_id=lesson_id,
        title=f"{request.topic.title()} — Track {request.track.value.replace('_', ' ').title()}",
        track=request.track,
        blocks=blocks,
        has_research_missions=state["has_research_missions"],
        oas_standards=state["oas_standards"],
        researcher_activated=state["researcher_activated"],
    )
