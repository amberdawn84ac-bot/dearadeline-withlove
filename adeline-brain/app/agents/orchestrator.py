"""
LangGraph Multi-Agent Orchestrator
Routes lesson requests to the appropriate specialist agent based on Track.
Enforces the Witness Protocol before any content reaches the student.

4 Specialist Agents:
  historian_agent     — TRUTH_HISTORY, JUSTICE_CHANGEMAKING
                        Strictest Witness Protocol; PRIMARY_SOURCE focus
  science_agent       — CREATION_SCIENCE, HOMESTEADING
                        LAB_MISSION blocks for hands-on tracks; homestead lens
  discipleship_agent  — HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS,
                        DISCIPLESHIP, ENGLISH_LITERATURE
                        Worldview alignment; NARRATIVE + scripture integration
  registrar_agent     — ALL tracks (post-processing)
                        Emits xAPI LearningActivity records + CASE credit entry

Researcher Upgrade: when Hippocampus returns ARCHIVE_SILENT, the orchestrator
calls SearchWitnesses (Tavily → scrape → cosine) before falling back to a
RESEARCH_MISSION block. If a verified source is found, the lesson continues
with a PRIMARY_SOURCE block from the auto-found archive.
"""
import uuid
import logging
from datetime import datetime, timezone
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

# Track routing constants
_HISTORIAN_TRACKS  = {Track.TRUTH_HISTORY, Track.JUSTICE_CHANGEMAKING}
_SCIENCE_TRACKS    = {Track.CREATION_SCIENCE, Track.HOMESTEADING}
_DISCIPLESHIP_TRACKS = {
    Track.HEALTH_NATUROPATHY, Track.GOVERNMENT_ECONOMICS,
    Track.DISCIPLESHIP, Track.ENGLISH_LITERATURE,
}


# ── Agent State ───────────────────────────────────────────────────────────────

class AdelineState(TypedDict):
    request:              LessonRequest
    lesson_id:            str
    query_embedding:      list[float]
    blocks:               list[dict]
    oas_standards:        list[dict]
    has_research_missions: bool
    researcher_activated: bool
    agent_name:           str
    xapi_statements:      list[dict]
    credits_awarded:      list[dict]


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
                "standard_id":          row.get("standard_id", ""),
                "text":                 row.get("text", ""),
                "grade":                row.get("grade", 0),
                "lesson_hook":          row.get("lesson_hook", ""),
                "connected_track":      row.get("connected_track", ""),
                "source_type":          "cross_track",
                "bridge_standard_text": row.get("bridge_standard_text", ""),
            })
    except Exception as e:
        logger.warning(f"[Neo4j] cross-track query failed for track={track}: {e}")

    return results


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _homestead_adapt(content: str) -> str:
    return (
        f"[Homestead Lens] {content[:300]}...\n\n"
        "*How does this connect to caring for your land and family?*"
    )


async def _researcher_fallback(
    state: AdelineState, track_value: str, source_title: str = ""
) -> dict | None:
    """Call SearchWitnesses and return a PRIMARY_SOURCE block dict, or None."""
    request = state["request"]
    witness = await search_witnesses(
        topic=request.topic,
        track=track_value,
        query_embedding=state["query_embedding"],
        lesson_id=state["lesson_id"],
    )
    if witness:
        state["researcher_activated"] = True
        content = witness.evidence.chunk
        return {
            "block_type":       BlockType.PRIMARY_SOURCE.value,
            "content": (
                f"*[Adeline searched the archives and found:]*\n\n{content}"
            ),
            "evidence":         [witness.evidence.model_dump()],
            "is_silenced":      False,
            "homestead_content": (
                _homestead_adapt(content) if request.is_homestead else None
            ),
        }
    return None


# ── Historian Agent (TRUTH_HISTORY, JUSTICE_CHANGEMAKING) ─────────────────────

async def historian_agent(state: AdelineState) -> AdelineState:
    """
    Truth-Based History specialist.
    Covers TRUTH_HISTORY and JUSTICE_CHANGEMAKING tracks.
    PRIMARY_SOURCE blocks when VERIFIED.
    On ARCHIVE_SILENT: tries SearchWitnesses before falling back to RESEARCH_MISSION.
    Most strict application of the Witness Protocol.
    """
    request = state["request"]
    state["agent_name"] = "HistorianAgent"
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

        if evidence.verdict == EvidenceVerdict.ARCHIVE_SILENT:
            logger.info(
                f"[Orchestrator] ARCHIVE_SILENT on '{result['source_title']}' — "
                "activating Researcher..."
            )
            block = await _researcher_fallback(state, request.track.value, result["source_title"])
            if block:
                blocks.append(block)
            else:
                mission = build_research_mission_block(request.topic, [result["source_title"]])
                blocks.append({
                    **mission,
                    "block_type": BlockType.RESEARCH_MISSION.value,
                    "evidence":   [evidence.model_dump()],
                })
                state["has_research_missions"] = True
        else:
            content = result["chunk"]
            blocks.append({
                "block_type":       BlockType.PRIMARY_SOURCE.value,
                "content":          content,
                "evidence":         [evidence.model_dump()],
                "is_silenced":      False,
                "homestead_content": (
                    _homestead_adapt(content) if request.is_homestead else None
                ),
            })

    if not blocks:
        logger.info("[Orchestrator] Empty Hippocampus result — activating Researcher...")
        block = await _researcher_fallback(state, request.track.value)
        if block:
            blocks.append(block)
        else:
            mission = build_research_mission_block(request.topic, [])
            blocks.append({
                **mission,
                "block_type": BlockType.RESEARCH_MISSION.value,
                "evidence":   [],
            })
            state["has_research_missions"] = True

    state["blocks"] = blocks
    return state


# ── Science Agent (CREATION_SCIENCE, HOMESTEADING) ────────────────────────────

async def science_agent(state: AdelineState) -> AdelineState:
    """
    Creation Science and Homesteading specialist.
    HOMESTEADING track uses LAB_MISSION blocks for hands-on, land-based learning.
    CREATION_SCIENCE uses PRIMARY_SOURCE blocks with direct observation lens.
    Homestead flag deepens the application to real farm/land activities.
    Witness Protocol applies; ARCHIVE_SILENT triggers Researcher.
    """
    request = state["request"]
    state["agent_name"] = "ScienceAgent"
    blocks: list[dict] = []
    is_homesteading = request.track == Track.HOMESTEADING

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

        if evidence.verdict == EvidenceVerdict.ARCHIVE_SILENT:
            logger.info(
                f"[ScienceAgent] ARCHIVE_SILENT on '{result['source_title']}' — "
                "activating Researcher..."
            )
            block = await _researcher_fallback(state, request.track.value, result["source_title"])
            if block:
                if is_homesteading:
                    # Promote to LAB_MISSION for hands-on homestead track
                    block["block_type"] = BlockType.LAB_MISSION.value
                    block["content"] = (
                        f"**Homestead Lab Mission**\n\n"
                        f"{block['content']}\n\n"
                        "*Observe this directly on your land. Record what you find.*"
                    )
                blocks.append(block)
            else:
                mission = build_research_mission_block(request.topic, [result["source_title"]])
                blocks.append({
                    **mission,
                    "block_type": BlockType.RESEARCH_MISSION.value,
                    "evidence":   [evidence.model_dump()],
                })
                state["has_research_missions"] = True

        elif evidence.verdict == EvidenceVerdict.VERIFIED:
            content = result["chunk"]
            block_type = BlockType.LAB_MISSION if is_homesteading else BlockType.PRIMARY_SOURCE
            lab_content = (
                f"**Homestead Lab Mission**\n\n{content}\n\n"
                "*Observe this directly on your land. Record what you find.*"
                if is_homesteading else content
            )
            blocks.append({
                "block_type":       block_type.value,
                "content":          lab_content,
                "evidence":         [evidence.model_dump()],
                "is_silenced":      False,
                "homestead_content": _homestead_adapt(content) if request.is_homestead else None,
            })

    if not blocks:
        logger.info("[ScienceAgent] Empty Hippocampus result — activating Researcher...")
        block = await _researcher_fallback(state, request.track.value)
        if block:
            if is_homesteading:
                block["block_type"] = BlockType.LAB_MISSION.value
                block["content"] = (
                    f"**Homestead Lab Mission**\n\n"
                    f"{block['content']}\n\n"
                    "*Observe this directly on your land. Record what you find.*"
                )
            blocks.append(block)
        else:
            mission = build_research_mission_block(request.topic, [])
            blocks.append({
                **mission,
                "block_type": BlockType.RESEARCH_MISSION.value,
                "evidence":   [],
            })
            state["has_research_missions"] = True

    state["blocks"] = blocks
    return state


# ── Discipleship Agent ─────────────────────────────────────────────────────────
# Covers: HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP, ENGLISH_LITERATURE

async def discipleship_agent(state: AdelineState) -> AdelineState:
    """
    Worldview, Character, and Cultural Discernment specialist.
    Covers HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP, ENGLISH_LITERATURE.

    Produces NARRATIVE blocks that weave source material into a worldview-aligned
    framing (scripture context, character formation, cultural discernment).
    VERIFIED sources are presented with interpretive narrative wrap.
    ARCHIVE_SILENT: tries Researcher; falls back to RESEARCH_MISSION.
    """
    request = state["request"]
    state["agent_name"] = "DiscipleshipAgent"
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

        if evidence.verdict == EvidenceVerdict.ARCHIVE_SILENT:
            logger.info(
                f"[DiscipleshipAgent] ARCHIVE_SILENT on '{result['source_title']}' — "
                "activating Researcher..."
            )
            block = await _researcher_fallback(state, request.track.value, result["source_title"])
            if block:
                # Wrap in worldview narrative
                block["block_type"] = BlockType.NARRATIVE.value
                block["content"] = _worldview_wrap(block["content"], request.track)
                blocks.append(block)
            else:
                mission = build_research_mission_block(request.topic, [result["source_title"]])
                blocks.append({
                    **mission,
                    "block_type": BlockType.RESEARCH_MISSION.value,
                    "evidence":   [evidence.model_dump()],
                })
                state["has_research_missions"] = True

        elif evidence.verdict == EvidenceVerdict.VERIFIED:
            content = result["chunk"]
            blocks.append({
                "block_type":       BlockType.NARRATIVE.value,
                "content":          _worldview_wrap(content, request.track),
                "evidence":         [evidence.model_dump()],
                "is_silenced":      False,
                "homestead_content": (
                    _homestead_adapt(content) if request.is_homestead else None
                ),
            })

    if not blocks:
        logger.info("[DiscipleshipAgent] Empty Hippocampus result — activating Researcher...")
        block = await _researcher_fallback(state, request.track.value)
        if block:
            block["block_type"] = BlockType.NARRATIVE.value
            block["content"] = _worldview_wrap(block["content"], request.track)
            blocks.append(block)
        else:
            mission = build_research_mission_block(request.topic, [])
            blocks.append({
                **mission,
                "block_type": BlockType.RESEARCH_MISSION.value,
                "evidence":   [],
            })
            state["has_research_missions"] = True

    state["blocks"] = blocks
    return state


def _worldview_wrap(content: str, track: Track) -> str:
    """Wrap source content with a worldview-alignment framing per track."""
    lead = {
        Track.DISCIPLESHIP:          "Through a biblical worldview lens:",
        Track.HEALTH_NATUROPATHY:    "Considering how God designed the body:",
        Track.GOVERNMENT_ECONOMICS:  "Applying stewardship and justice principles:",
        Track.ENGLISH_LITERATURE:    "Reading through a discerning, truth-seeking lens:",
    }.get(track, "Viewing this through a biblical worldview:")
    return (
        f"*{lead}*\n\n"
        f"{content}\n\n"
        "*How does this shape your understanding of God's design and your calling?*"
    )


# ── Registrar Agent (post-processing, all tracks) ─────────────────────────────

async def registrar_agent(state: AdelineState) -> AdelineState:
    """
    CASE credit and xAPI record emitter — runs after every specialist agent.

    For each completed lesson block it emits one xAPI LearningActivity statement.
    For the lesson as a whole it generates a CASE-compatible credit entry.
    These are stored in state and returned on the LessonResponse for Phase 6
    persistence (adeline-brain/app/api/journal.py will write them to DB).
    """
    request   = state["request"]
    lesson_id = state["lesson_id"]
    now_iso   = datetime.now(timezone.utc).isoformat()
    blocks    = state["blocks"]

    # ── xAPI statements: one per block ────────────────────────────────────────
    xapi_statements: list[dict] = []
    for i, block in enumerate(blocks):
        verb = _block_type_to_xapi_verb(block.get("block_type", ""))
        xapi_statements.append({
            "id":        str(uuid.uuid4()),
            "timestamp": now_iso,
            "actor":     {"objectType": "Agent", "account": {"name": request.student_id}},
            "verb":      {
                "id":      f"http://adlnet.gov/expapi/verbs/{verb}",
                "display": {"en-US": verb},
            },
            "object":    {
                "id":         f"urn:adeline:lesson:{lesson_id}:block:{i}",
                "definition": {
                    "name": {"en-US": f"{request.topic} — Block {i + 1}"},
                    "type": "http://adlnet.gov/expapi/activities/lesson",
                },
            },
            "context":   {
                "extensions": {
                    "https://adeline.app/xapi/ext/track":       request.track.value,
                    "https://adeline.app/xapi/ext/grade_level": request.grade_level,
                    "https://adeline.app/xapi/ext/agent":       state.get("agent_name", ""),
                    "https://adeline.app/xapi/ext/is_homestead": request.is_homestead,
                    "https://adeline.app/xapi/ext/block_type":  block.get("block_type", ""),
                }
            },
        })

    # ── CASE credit entry: one per lesson ─────────────────────────────────────
    verified_count  = sum(
        1 for b in blocks
        if b.get("block_type") in (BlockType.PRIMARY_SOURCE.value, BlockType.NARRATIVE.value)
    )
    lab_count       = sum(1 for b in blocks if b.get("block_type") == BlockType.LAB_MISSION.value)
    credit_hours    = round(min(1.0, 0.1 * (verified_count + lab_count)), 2)

    credits_awarded: list[dict] = [{
        "id":                  str(uuid.uuid4()),
        "lesson_id":           lesson_id,
        "student_id":          request.student_id,
        "course_title":        f"{request.topic.title()} ({request.track.value.replace('_', ' ').title()})",
        "track":               request.track.value,
        "oas_standards":       [s.get("standard_id", "") for s in state.get("oas_standards", [])],
        "activity_description": (
            f"Lesson on '{request.topic}' via {state.get('agent_name', 'Adeline')} — "
            f"{verified_count} verified source(s)"
            + (f", {lab_count} lab mission(s)" if lab_count else "")
        ),
        "credit_hours":        credit_hours,
        "credit_type":         _track_to_credit_type(request.track),
        "is_homestead_credit": request.is_homestead,
        "completed_at":        now_iso,
        "researcher_activated": state["researcher_activated"],
    }]

    state["xapi_statements"] = xapi_statements
    state["credits_awarded"]  = credits_awarded
    logger.info(
        f"[RegistrarAgent] Emitted {len(xapi_statements)} xAPI statement(s) + "
        f"{credit_hours} credit hours for student={request.student_id}"
    )
    return state


def _block_type_to_xapi_verb(block_type: str) -> str:
    return {
        BlockType.PRIMARY_SOURCE.value:   "experienced",
        BlockType.NARRATIVE.value:        "experienced",
        BlockType.LAB_MISSION.value:      "attempted",
        BlockType.RESEARCH_MISSION.value: "interacted",
        BlockType.QUIZ.value:             "attempted",
        BlockType.TEXT.value:             "experienced",
    }.get(block_type, "experienced")


def _track_to_credit_type(track: Track) -> str:
    return {
        Track.TRUTH_HISTORY:        "CORE",
        Track.CREATION_SCIENCE:     "CORE",
        Track.ENGLISH_LITERATURE:   "CORE",
        Track.GOVERNMENT_ECONOMICS: "CORE",
        Track.JUSTICE_CHANGEMAKING: "CORE",
        Track.DISCIPLESHIP:         "ELECTIVE",
        Track.HEALTH_NATUROPATHY:   "ELECTIVE",
        Track.HOMESTEADING:         "HOMESTEAD",
    }.get(track, "ELECTIVE")


# ── Router ────────────────────────────────────────────────────────────────────

def _route(state: AdelineState) -> Literal["historian", "science", "discipleship"]:
    track = state["request"].track
    if track in _HISTORIAN_TRACKS:
        return "historian"
    if track in _SCIENCE_TRACKS:
        return "science"
    return "discipleship"


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def run_orchestrator(
    request: LessonRequest, query_embedding: list[float]
) -> LessonResponse:
    """
    Routes the request to the correct specialist agent, graph-links to
    OAS Standards via Neo4j, runs the RegistrarAgent for xAPI + CASE credits,
    and returns a structured LessonResponse.

    Agent routing:
      TRUTH_HISTORY, JUSTICE_CHANGEMAKING  → HistorianAgent
      CREATION_SCIENCE, HOMESTEADING       → ScienceAgent
      All other tracks                     → DiscipleshipAgent

    RegistrarAgent always runs last as a post-processing step regardless of track.

    When Hippocampus lacks verified sources (ARCHIVE_SILENT), the Researcher
    tool automatically searches archive.org, gutenberg.org, and archives.gov
    before falling back to a student-facing RESEARCH_MISSION.
    """
    lesson_id = str(uuid.uuid4())

    state: AdelineState = {
        "request":              request,
        "lesson_id":            lesson_id,
        "query_embedding":      query_embedding,
        "blocks":               [],
        "oas_standards":        [],
        "has_research_missions": False,
        "researcher_activated": False,
        "agent_name":           "",
        "xapi_statements":      [],
        "credits_awarded":      [],
    }

    route = _route(state)
    logger.info(
        f"[Orchestrator] Routing to: {route} | "
        f"track={request.track.value} | topic='{request.topic}'"
    )

    # ── 1. Specialist agent ────────────────────────────────────────────────────
    if route == "historian":
        state = await historian_agent(state)
    elif route == "science":
        state = await science_agent(state)
    else:
        state = await discipleship_agent(state)

    # ── 2. Graph context (Neo4j) ───────────────────────────────────────────────
    state["oas_standards"] = await _fetch_graph_context(request.track.value)
    primary_count = sum(1 for s in state["oas_standards"] if s.get("source_type") == "primary")
    cross_count   = sum(1 for s in state["oas_standards"] if s.get("source_type") == "cross_track")

    # ── 3. Registrar (xAPI + CASE credits) ────────────────────────────────────
    state = await registrar_agent(state)

    logger.info(
        f"[Orchestrator] agent={state['agent_name']} | "
        f"graph: {primary_count} primary + {cross_count} cross-track | "
        f"blocks: {len(state['blocks'])} | "
        f"research_missions: {state['has_research_missions']} | "
        f"researcher_activated: {state['researcher_activated']} | "
        f"xapi_statements: {len(state['xapi_statements'])} | "
        f"credits: {len(state['credits_awarded'])}"
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
        agent_name=state["agent_name"],
        xapi_statements=state["xapi_statements"],
        credits_awarded=state["credits_awarded"],
    )
