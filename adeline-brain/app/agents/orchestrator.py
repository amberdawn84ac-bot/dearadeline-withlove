"""
LangGraph Multi-Agent Orchestrator
Routes lesson requests to the appropriate specialist agent based on Track.
Enforces the Witness Protocol before any content reaches the student.

6 Specialist Agents:
  historian_agent     — TRUTH_HISTORY
                        Strictest Witness Protocol (0.82); PRIMARY_SOURCE focus
  justice_agent       — JUSTICE_CHANGEMAKING
                        Power-capture framing; primary source evidence
  science_agent       — CREATION_SCIENCE, HOMESTEADING
                        LAB_MISSION blocks for hands-on tracks; homestead lens
  literature_agent    — ENGLISH_LITERATURE
                        Book-context aware; literary analysis without Witness gate
  practical_agent     — APPLIED_MATHEMATICS, CREATIVE_ECONOMY
                        Applied skills; Claude synthesis without Witness gate
  discipleship_agent  — HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP
                        Worldview alignment; NARRATIVE + scripture integration
  registrar_agent     — ALL tracks (post-processing)
                        Emits xAPI LearningActivity records + CASE credit entry

Researcher Upgrade: when Hippocampus returns ARCHIVE_SILENT, the orchestrator
calls SearchWitnesses (Tavily → scrape → cosine) before falling back to a
RESEARCH_MISSION block. If a verified source is found, the lesson continues
with a PRIMARY_SOURCE block from the auto-found archive.
"""
import uuid
import os
import logging
from datetime import datetime, timezone
from typing import TypedDict, Literal

import anthropic

from app.schemas.api_models import (
    LessonRequest, LessonResponse, LessonBlockResponse,
    Track, BlockType, EvidenceVerdict,
)
from app.protocols.witness import evaluate_evidence, build_research_mission_block
from app.connections.pgvector_client import hippocampus
from app.connections.neo4j_client import neo4j_client
from app.tools.researcher import search_witnesses

_ANTHROPIC_MODEL = os.getenv("ADELINE_MODEL", "claude-sonnet-4-6")

logger = logging.getLogger(__name__)

# Track routing constants
# TRUTH_HISTORY is the ONLY track that requires the Witness Protocol —
# every block must be backed by a verified primary source (cosine ≥ 0.82).
_HISTORIAN_TRACKS  = {Track.TRUTH_HISTORY}
_JUSTICE_TRACKS    = {Track.JUSTICE_CHANGEMAKING}
_SCIENCE_TRACKS    = {Track.CREATION_SCIENCE, Track.HOMESTEADING}
_DISCIPLESHIP_TRACKS = {
    Track.HEALTH_NATUROPATHY, Track.GOVERNMENT_ECONOMICS,
    Track.DISCIPLESHIP,
}
_LITERATURE_TRACKS = {Track.ENGLISH_LITERATURE}


# ── Claude synthesis ─────────────────────────────────────────────────────────

# Grade band → readable description and age mapping
_GRADE_DESC = {
    "K": "kindergarten (age 5-6)", "1": "1st grade (age 6-7)", "2": "2nd grade (age 7-8)",
    "3": "3rd grade (age 8-9)", "4": "4th grade (age 9-10)", "5": "5th grade (age 10-11)",
    "6": "6th grade (age 11-12)", "7": "7th grade (age 12-13)", "8": "8th grade (age 13-14)",
    "9": "9th grade (age 14-15)", "10": "10th grade (age 15-16)",
    "11": "11th grade (age 16-17)", "12": "12th grade (age 17-18)",
}

# Grade → minimum age mapping (lower bound for content filtering)
_GRADE_TO_MIN_AGE = {
    "K": 5, "1": 6, "2": 7, "3": 8, "4": 9, "5": 10, "6": 11,
    "7": 12, "8": 13, "9": 14, "10": 15, "11": 16, "12": 17,
}

# Per-track character voice for synthesis
_TRACK_PERSONA = {
    Track.TRUTH_HISTORY: (
        "a truth-first historian. You show what actually happened — not the sanitized textbook version. "
        "You put primary sources in front of students and let them read real words from real people. "
        "You name the people in power who lied, and the people they harmed. You don't editorialize. "
        "You let the documents speak."
    ),
    Track.JUSTICE_CHANGEMAKING: (
        "a justice investigator. Your job is to show students exactly what happened, "
        "who got hurt, and who profited. You focus on three categories of harm: "
        "(1) NATION-BUILDING PROPAGANDA — government and corporate narratives designed to "
        "justify wars, displacement, and exploitation. You name the specific lies, who told them, "
        "and who benefited financially or politically. "
        "(2) CORPORATE CRIMES — deliberate harm for profit. Pharma companies that hid trial data. "
        "Food companies that funded research to blame fat instead of sugar. Chemical companies that "
        "knew their products caused cancer. Oil companies that buried their own climate science. "
        "You always name the company, the executive, the internal memo if it exists, and the body count. "
        "(3) JUSTICE FOR PEOPLE HARMED — you center the victims by name. Not statistics. "
        "Real people. What happened to them. What it cost them. Whether anyone was held accountable. "
        "You teach students to follow the money: find the lobbying disclosures, read the court documents, "
        "look at who funded the science, trace the revolving door between regulators and industry. "
        "You treat students as investigators who can use the same tools journalists and lawyers use."
    ),
    Track.CREATION_SCIENCE: (
        "a creation science mentor who sees YHWH's fingerprints on every natural law. "
        "You teach science through awe and hands-on discovery. You don't sanitize the hard questions — "
        "you name them and work through them honestly. You connect every concept back to how God designed it."
    ),
    Track.HOMESTEADING: (
        "a self-sufficiency mentor. Your whole frame is: what happens if the grid goes down tomorrow? "
        "No electricity. No grocery store. No pharmacy. No lumber yard. "
        "Every skill you teach is something a family actually needs to survive and thrive on their own. "
        "You are practical, direct, and allergic to theory that doesn't build anything."
    ),
    Track.DISCIPLESHIP: (
        "a discipleship guide who takes Scripture seriously in its original context. "
        "You draw from Hebrew and Greek roots when they matter. "
        "No churchy clichés. No hollow motivation. Just truth, plainly spoken. "
        "You connect what YHWH says to what is actually happening in the world right now."
    ),
    Track.HEALTH_NATUROPATHY: (
        "a health mentor who has watched the medical system harm people who trusted it. "
        "You teach how the body actually works, what actually heals it, and what the pharmaceutical industry "
        "doesn't want families to know. You honor how YHWH designed the body. "
        "You give families real knowledge so they are never dependent on a system that profits from their sickness."
    ),
    Track.GOVERNMENT_ECONOMICS: (
        "a systems mentor who teaches how power actually works — not how civics textbooks say it works. "
        "You explain money flows, lobbying, regulatory capture, and who actually benefits. "
        "You teach students to build alternative systems, not just understand broken ones. "
        "You treat them as capable of both seeing corruption clearly and doing something about it."
    ),
    Track.ENGLISH_LITERATURE: (
        "a literature mentor who reads every story as a truth claim about the world. "
        "You teach students to read critically — to notice what an author believes, "
        "what they're asking the reader to accept, and whether it holds up. "
        "You connect great writing to real courage. You point to books that shaped movements."
    ),
    Track.APPLIED_MATHEMATICS: (
        "a practical math mentor. Your whole frame is: math you will actually use in real life. "
        "Budgeting, interest, measuring land, building structures, pricing crops for market, "
        "calculating yields, understanding loans, reading a balance sheet. "
        "You never teach a formula without showing exactly where a person would use it this week. "
        "Math is a tool — not a performance. Show them how it works in the real world."
    ),
    Track.CREATIVE_ECONOMY: (
        "a maker-entrepreneur mentor. You teach students to create beautiful, functional things "
        "with their hands — and sell them. Upcycled furniture, handmade goods, farm products, "
        "branded packaging, market displays. You teach craft, pricing, marketing, and the satisfaction "
        "of building something real. Every project ends with a finished product worth money. "
        "You treat creativity as a survival skill, not a hobby."
    ),
}

# Brand voice rules injected into every synthesis call
_ADELINE_VOICE = """
BRAND VOICE (non-negotiable):
• Clear, strong sentences. No fluff. No busywork.
• Write like you are telling the truth to someone at the kitchen table — not giving a lecture.
• Short paragraphs. Active verbs. Specific details.
• Do not soften hard truths. If something is corrupt, say it's corrupt.
• Do not use academic or corporate language. No "it is important to note that..."
• Scripture references should feel natural, not pasted in. Draw from real context, not clichés.
• Treat the student like a leader in training — capable of doing something hard right now.
• No "Today we will learn..." openers. No "Great job!" closings. No filler.
• If the source reveals injustice, name it plainly and connect it to purpose.
"""


async def _synthesize_content(
    request: LessonRequest,
    block_type: str,
    source_chunks: list[dict],
    raw_content: str,
) -> str:
    """
    Call Claude to synthesize lesson content from verified sources using Adeline's voice.

    If the Anthropic API key is absent, returns raw_content unchanged.

    Claude's job:
      1. Write at the student's grade level
      2. Match Adeline's voice — direct, plain, truth-first, justice-aware
      3. Ground every claim in the provided source
      4. No busywork, no padding, no academic tone
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return raw_content

    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    persona    = _TRACK_PERSONA.get(request.track, "a knowledgeable mentor")
    track_name = request.track.value.replace("_", " ").title()

    sources_text = "\n\n---\n\n".join(
        f"[SOURCE: {c['source_title']} — {c.get('citation_author', 'Unknown')}, "
        f"{c.get('citation_year', 'n.d.')}]\n{c['chunk']}"
        for c in source_chunks
    )

    block_label = block_type.replace("_", " ").lower()

    system_prompt = (
        f"You are Adeline — {persona}\n\n"
        f"You are writing for a {grade_desc} student in a Christian homeschool family.\n\n"
        f"{_ADELINE_VOICE}\n"
        "CONTENT RULES:\n"
        "• Use ONLY the provided source text — never invent facts\n"
        "• 2–3 paragraphs maximum\n"
        "• End with one direct question or challenge — not 'What did you learn?' but something that demands thought or action\n"
    )

    user_prompt = (
        f"Topic: {request.topic}\n"
        f"Track: {track_name}\n"
        f"Block type: {block_label}\n\n"
        f"Source(s):\n{sources_text}\n\n"
        f"Write the {block_label} content in Adeline's voice. "
        f"Ground every claim in the source. Make it land."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.warning(f"[Claude] Synthesis failed ({e}) — using raw chunk")
        return raw_content


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
    interaction_count:    int
    cross_track_acknowledgment: str | None


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

    # Get student age from grade level for content filtering
    student_age = _GRADE_TO_MIN_AGE.get(request.grade_level)

    witness_list = await search_witnesses(
        query=request.topic,
        track=track_value,
        top_k=1,
        student_age=student_age,
    )
    if witness_list:
        state["researcher_activated"] = True
        best_evidence = witness_list[0]
        content = best_evidence['chunk']
        return {
            "block_type":       BlockType.PRIMARY_SOURCE.value,
            "content": (
                f"*[Adeline searched the archives and found:]*\n\n{content}"
            ),
            "evidence":         [best_evidence],
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

    silent_sources: list[str] = []

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
            track=request.track.value,
        )

        if evidence.verdict == EvidenceVerdict.ARCHIVE_SILENT:
            # Collect silent sources — try researcher once at the end, not per-result
            silent_sources.append(result["source_title"])
        else:
            raw = result["chunk"]
            content = await _synthesize_content(
                request=request,
                block_type=BlockType.PRIMARY_SOURCE.value,
                source_chunks=[result],
                raw_content=raw,
            )
            blocks.append({
                "block_type":       BlockType.PRIMARY_SOURCE.value,
                "content":          content,
                "evidence":         [evidence.model_dump()],
                "is_silenced":      False,
                "homestead_content": (
                    _homestead_adapt(raw) if request.is_homestead else None
                ),
            })

    # If no verified blocks, try researcher once (not per silent result)
    if not blocks:
        logger.info(
            f"[HistorianAgent] No verified sources for '{request.topic}' — "
            "activating Researcher..."
        )
        block = await _researcher_fallback(state, request.track.value)
        if block:
            blocks.append(block)
        else:
            # Researcher also failed — Claude provides orientation + single research mission
            orientation = await _synthesize_content(
                request=request,
                block_type=BlockType.NARRATIVE.value,
                source_chunks=[],
                raw_content=request.topic,
            )
            blocks.append({
                "block_type":  BlockType.NARRATIVE.value,
                "content":     orientation,
                "evidence":    [],
                "is_silenced": False,
                "homestead_content": None,
            })
            mission = build_research_mission_block(request.topic, silent_sources[:3])
            blocks.append({
                **mission,
                "block_type": BlockType.RESEARCH_MISSION.value,
                "evidence":   [],
            })
            state["has_research_missions"] = True

    # ── Multimodal synthesis ─────────────────────────────────────────────────
    await _run_multimodal_synthesis(state, blocks, allow_timeline=True)

    state["blocks"] = blocks
    return state


# ── Justice Agent (JUSTICE_CHANGEMAKING) ─────────────────────────────────────

async def justice_agent(state: AdelineState) -> AdelineState:
    """
    Justice Changemaking specialist — investigative journalism model.

    Does NOT require the Witness Protocol. Justice teaches students to BE
    investigators. The lesson is an investigation brief, not a verified archive.

    Three focal areas (always present at least one per lesson):
      1. Nation-building propaganda — name the lie, who told it, who profited
      2. Corporate crimes — deliberate harm for profit, name company + body count
      3. People harmed — center victims by name, not as statistics

    Block structure:
      NARRATIVE  — presents the harm clearly: who, what, how much they profited
      RESEARCH_MISSION — gives the student a specific place to look for evidence
                         (lobbying disclosures, court records, internal memos, etc.)
    """
    request = state["request"]
    state["agent_name"] = "JusticeAgent"
    blocks: list[dict] = []

    # Pull any seeded primary sources as background context (not for Witness gatekeeping)
    raw_results = await hippocampus.similarity_search(
        query_embedding=state["query_embedding"],
        track=request.track.value,
        top_k=3,
    )

    source_context = "\n\n".join(
        f"[Source: {r['source_title']}]\n{r['chunk']}"
        for r in raw_results
    ) if raw_results else ""

    grade_desc = _GRADE_DESC.get(request.grade_level or "8", "middle school")
    persona    = _TRACK_PERSONA[Track.JUSTICE_CHANGEMAKING]

    investigation_prompt = f"""You are {persona}

Grade level: {grade_desc}
Topic: {request.topic}

{"Background sources from the archive:\\n" + source_context if source_context else "No archive sources found. Rely on well-documented public knowledge."}

Write a justice investigation lesson in two parts:

PART 1 — THE BRIEF (NARRATIVE block):
Open with the specific harm. Name it plainly. Then:
• Who was hurt? Name real people if possible — not "communities" or "workers."
• Who profited? Name the company, the executive, the dollar amount if known.
• What mechanism did they use? (propaganda campaign, regulatory capture, buried research, legislative capture, media control)
• What did they know and when? If there are internal documents, name them.
• One sentence on whether anyone faced accountability — and if not, say so plainly.

PART 2 — THE INVESTIGATION (RESEARCH_MISSION block):
Give the student exactly ONE specific investigation task. Not "research the topic."
A real task: find a specific document, read a specific database, look up a specific filing.
Examples of good tasks:
  • "Go to opensecrets.org and find how much [company] spent lobbying [agency] in [year range]."
  • "Search the FDA adverse event database for [drug name] and count how many deaths were reported."
  • "Read the 1969 internal Sugar Research Foundation memo at UCSF's tobacco documents archive."
  • "Look up [company] v. [plaintiff] in PACER — read the plaintiff's complaint, paragraph 12."

Format your response as:

NARRATIVE:
[The investigation brief — plain, direct, no academic language]

RESEARCH_MISSION:
[The specific task — one concrete action with a real URL or database name]

{_ADELINE_VOICE}
"""

    if not os.getenv("ANTHROPIC_API_KEY"):
        blocks.append({
            "block_type":  BlockType.NARRATIVE.value,
            "content":     f"Justice investigation: {request.topic}",
            "evidence":    [],
            "is_silenced": False,
        })
        state["blocks"] = blocks
        return state

    raw_output = ""
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": investigation_prompt}],
        )
        raw_output = message.content[0].text.strip()
    except Exception as e:
        logger.warning(f"[JusticeAgent] Claude call failed ({e}) — using fallback NARRATIVE")
        blocks.append({
            "block_type":  BlockType.NARRATIVE.value,
            "content":     f"Justice investigation: {request.topic}",
            "evidence":    [],
            "is_silenced": False,
        })
        state["blocks"] = blocks
        return state

    # Parse NARRATIVE and RESEARCH_MISSION sections
    narrative_text = ""
    mission_text   = ""
    if "RESEARCH_MISSION:" in raw_output:
        parts          = raw_output.split("RESEARCH_MISSION:", 1)
        narrative_text = parts[0].replace("NARRATIVE:", "").strip()
        mission_text   = parts[1].strip()
    else:
        narrative_text = raw_output.replace("NARRATIVE:", "").strip()

    if narrative_text:
        blocks.append({
            "block_type":  BlockType.NARRATIVE.value,
            "content":     narrative_text,
            "evidence":    [],
            "is_silenced": False,
        })

    if mission_text:
        blocks.append({
            "block_type":  BlockType.RESEARCH_MISSION.value,
            "content":     mission_text,
            "evidence":    [],
            "is_silenced": False,
        })
        state["has_research_missions"] = True

    if not blocks:
        mission = build_research_mission_block(request.topic, [])
        blocks.append({
            **mission,
            "block_type": BlockType.RESEARCH_MISSION.value,
            "evidence":   [],
        })
        state["has_research_missions"] = True

    # ── Multimodal synthesis ─────────────────────────────────────────────────
    await _run_multimodal_synthesis(state, blocks, allow_timeline=True)

    state["blocks"] = blocks
    return state


# ── Science Agent (CREATION_SCIENCE, HOMESTEADING) ────────────────────────────

async def science_agent(state: AdelineState) -> AdelineState:
    """
    Creation Science and Homesteading specialist — "Sovereign Lab" model.

    CREATION_SCIENCE: EXPERIMENT-FIRST. Adeline acts as a Lab Director.
      1. Check the experiment catalog for a matching "wow" experiment
      2. If found → EXPERIMENT block (hands-on, filmable, viral)
      3. If not  → fall back to Hippocampus retrieval (PRIMARY_SOURCE)

    HOMESTEADING: LAB_MISSION blocks for hands-on, land-based learning.

    The "No Busywork" science loop:
      Hook → Materials Check → Live Guide → Film It → Discovery Video = Portfolio

    Witness Protocol applies to text-based blocks; experiments are pre-verified
    via the curated experiment catalog and don't need cosine scoring.
    """
    from app.api.experiments import EXPERIMENTS

    request = state["request"]
    state["agent_name"] = "ScienceAgent"
    blocks: list[dict] = []
    is_homesteading = request.track == Track.HOMESTEADING
    is_creation_science = request.track == Track.CREATION_SCIENCE

    # ── Step 1: Experiment match (CREATION_SCIENCE only) ──────────────────────
    # Search the experiment catalog for concept keyword overlap with the topic.
    experiment_matched = False
    if is_creation_science:
        topic_lower = request.topic.lower()
        best_experiment = None
        best_overlap = 0

        for exp in EXPERIMENTS.values():
            # Score: number of concept keywords that appear in the topic
            overlap = sum(
                1 for concept in exp.scientific_concepts
                if concept.lower() in topic_lower or any(
                    word in topic_lower for word in concept.lower().split()
                )
            )
            # Also check title/tagline
            if exp.title.lower() in topic_lower or topic_lower in exp.title.lower():
                overlap += 3
            for word in topic_lower.split():
                if len(word) > 3 and word in exp.tagline.lower():
                    overlap += 1

            if overlap > best_overlap:
                best_overlap = overlap
                best_experiment = exp

        if best_experiment and best_overlap >= 1:
            experiment_matched = True
            logger.info(
                f"[ScienceAgent] Experiment match: '{best_experiment.title}' "
                f"(overlap={best_overlap}) for topic='{request.topic}'"
            )

            # Build the EXPERIMENT block with the Creation Connection
            content = (
                f"**{best_experiment.title}** {_CHAOS_EMOJI[best_experiment.chaos_level]}\n\n"
                f"*{best_experiment.tagline}*\n\n"
                f"We could read about {', '.join(best_experiment.scientific_concepts[:2])}, "
                f"OR we could make enough "
            )
            # Tailor the hook per experiment
            if "toothpaste" in best_experiment.title.lower():
                content += "foam to wash an elephant. Which one?"
            elif "mentos" in best_experiment.title.lower():
                content += "pressure to launch a soda rocket 50 feet into the air. Which one?"
            elif "oobleck" in best_experiment.title.lower():
                content += "non-Newtonian fluid to walk on. Which one?"
            elif "fire" in best_experiment.title.lower():
                content += "heat to build a real vortex of fire. Which one?"
            elif "dry ice" in best_experiment.title.lower():
                content += "CO\u2082 to fill a giant fog bubble. Which one?"
            else:
                content += f"something unforgettable. Ready?"

            blocks.append({
                "block_type":        BlockType.EXPERIMENT.value,
                "content":           content,
                "evidence":          [],  # experiments are pre-verified (curated catalog)
                "is_silenced":       False,
                "homestead_content": None,
                "experiment_id":     best_experiment.id,
                "experiment_data":   best_experiment.model_dump(),
            })

    # ── Step 2: Hippocampus retrieval (HOMESTEADING, or CREATION_SCIENCE fallback)
    if not experiment_matched:
        raw_results = await hippocampus.similarity_search(
            query_embedding=state["query_embedding"],
            track=request.track.value,
            top_k=3,
        )

        # No Witness Protocol threshold — science content doesn't need archival verification.
        # Hippocampus results are reference material; Claude synthesizes the actual lesson.
        for result in raw_results:
            raw = result["chunk"]
            block_type = BlockType.LAB_MISSION if is_homesteading else BlockType.PRIMARY_SOURCE
            content = await _synthesize_content(
                request=request,
                block_type=block_type.value,
                source_chunks=[result],
                raw_content=raw,
            )
            if is_homesteading:
                content = (
                    f"**Homestead Lab Mission**\n\n{content}\n\n"
                    "*Observe this directly on your land. Record what you find.*"
                )
            blocks.append({
                "block_type":        block_type.value,
                "content":           content,
                "evidence":          [{
                    "source_id":        result["id"],
                    "source_title":     result["source_title"],
                    "source_url":       result.get("source_url", ""),
                    "witness_citation": {
                        "author":       result.get("citation_author", ""),
                        "year":         result.get("citation_year"),
                        "archive_name": result.get("citation_archive_name", ""),
                    },
                    "similarity_score": float(result["similarity_score"]),
                    "verdict":          "VERIFIED",
                    "chunk":            raw,
                }],
                "is_silenced":       False,
                "homestead_content": _homestead_adapt(raw) if request.is_homestead else None,
            })

        if not blocks:
            # Hippocampus empty — try web search first (seeds Hippocampus for next time)
            logger.info("[ScienceAgent] Hippocampus empty — searching web to seed and generate.")
            web_results = await search_witnesses(request.topic, request.track.value)
            if web_results:
                raw = web_results[0].get("chunk", request.topic)
                block_type = BlockType.LAB_MISSION if is_homesteading else BlockType.PRIMARY_SOURCE
                content = await _synthesize_content(
                    request=request,
                    block_type=block_type.value,
                    source_chunks=web_results,
                    raw_content=raw,
                )
                if is_homesteading:
                    content = (
                        f"**Homestead Lab Mission**\n\n{content}\n\n"
                        "*Observe this directly on your land. Record what you find.*"
                    )
                blocks.append({
                    "block_type":        block_type.value,
                    "content":           content,
                    "evidence":          [{
                        "source_id":        r.get("source_id", ""),
                        "source_title":     r.get("source_title", ""),
                        "source_url":       r.get("source_url", ""),
                        "witness_citation": r.get("witness_citation", {}),
                        "similarity_score": float(r.get("similarity_score", 0)),
                        "verdict":          "VERIFIED",
                        "chunk":            r.get("chunk", ""),
                    } for r in web_results[:2]],
                    "is_silenced":       False,
                    "homestead_content": None,
                })
                state["researcher_activated"] = True
            else:
                # Web search also empty — Claude generates from its own knowledge
                logger.info("[ScienceAgent] No web results — generating from Claude knowledge.")
                block_type = BlockType.LAB_MISSION if is_homesteading else BlockType.PRIMARY_SOURCE
                content = await _synthesize_content(
                    request=request,
                    block_type=block_type.value,
                    source_chunks=[],
                    raw_content=request.topic,
                )
                if is_homesteading:
                    content = (
                        f"**Homestead Lab Mission**\n\n{content}\n\n"
                        "*Observe this directly on your land. Record what you find.*"
                    )
                blocks.append({
                    "block_type":        block_type.value,
                    "content":           content,
                    "evidence":          [],
                    "is_silenced":       False,
                    "homestead_content": None,
                })

    # ── Multimodal synthesis ─────────────────────────────────────────────────
    await _run_multimodal_synthesis(
        state, blocks,
        allow_timeline=is_homesteading,
        is_seasonal_timeline=is_homesteading,
    )

    state["blocks"] = blocks
    return state


# Chaos level emoji lookup
_CHAOS_EMOJI = {1: "🌱", 2: "🔭", 3: "🔥"}


# ── Tracks that skip the Witness Protocol ────────────────────────────────────
# These tracks use Hippocampus as reference material (if available) but don't
# gate on cosine similarity. Claude synthesizes practical content directly.
_PRACTICAL_TRACKS = {Track.APPLIED_MATHEMATICS, Track.CREATIVE_ECONOMY}


# ── Literature Agent (ENGLISH_LITERATURE) ────────────────────────────────────

async def _get_active_book(student_id: str) -> dict | None:
    """Fetch the student's currently reading book from ReadingSession + Book."""
    try:
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                """
                SELECT b.id, b.title, b.author, b.track, b.lexile_level, b.grade_band,
                       rs."currentLocation", rs."pagesRead", rs."totalPages"
                FROM "ReadingSession" rs
                JOIN "Book" b ON b.id = rs."bookId"
                WHERE rs."studentId" = $1 AND rs.status = 'reading'
                ORDER BY rs."updatedAt" DESC
                LIMIT 1
                """,
                student_id,
            )
        finally:
            await conn.close()
        if row:
            return dict(row)
    except Exception as e:
        logger.warning(f"[LiteratureAgent] Failed to fetch active book: {e}")
    return None


async def literature_agent(state: AdelineState) -> AdelineState:
    """
    English Literature specialist — literary analysis, not fact-checking.

    Does NOT use the Witness Protocol. Literature is about interpretation,
    not historical verification. A novel is not a declassified document.

    Priority:
      1. If student has an active book in ReadingNook → analyze that book
      2. If Hippocampus has relevant literature content → use as reference
      3. Otherwise → Claude generates literary discussion from its knowledge

    Always produces NARRATIVE blocks with literary analysis framing.
    """
    request = state["request"]
    state["agent_name"] = "LiteratureAgent"
    blocks: list[dict] = []

    # ── Step 1: Check for active book in ReadingNook ─────────────────────────
    active_book = await _get_active_book(request.student_id)

    if active_book:
        logger.info(
            f"[LiteratureAgent] Student reading: '{active_book['title']}' "
            f"by {active_book['author']}"
        )
        # Synthesize literary analysis grounded in the book they're reading
        content = await _synthesize_literature(
            request=request,
            book_title=active_book["title"],
            book_author=active_book["author"],
            topic=request.topic,
        )
        blocks.append({
            "block_type":       BlockType.NARRATIVE.value,
            "content":          _worldview_wrap(content, request.track),
            "evidence":         [{
                "source_id":        f"book-{active_book['id']}",
                "source_title":     f"{active_book['title']} by {active_book['author']}",
                "source_url":       "",
                "witness_citation": {
                    "author": active_book["author"],
                    "year": None,
                    "archive_name": "Student's Reading Nook",
                },
                "similarity_score": 1.0,
                "verdict":          "VERIFIED",
                "chunk":            f"Literary analysis of {active_book['title']}",
            }],
            "is_silenced":      False,
            "homestead_content": None,
        })
        # Fall through to multimodal synthesis below

    else:
        # ── Step 2: Hippocampus reference (no Witness gate) ──────────────────────
        raw_results = await hippocampus.similarity_search(
            query_embedding=state["query_embedding"],
            track=request.track.value,
            top_k=3,
        )

        reference_chunks = []
        for result in raw_results:
            reference_chunks.append(result)

        # ── Step 3: Synthesize literary content ───────────────────────────────────
        if reference_chunks:
            content = await _synthesize_content(
                request=request,
                block_type=BlockType.NARRATIVE.value,
                source_chunks=reference_chunks,
                raw_content=reference_chunks[0]["chunk"],
            )
            blocks.append({
                "block_type":       BlockType.NARRATIVE.value,
                "content":          _worldview_wrap(content, request.track),
                "evidence":         [{
                    "source_id":        r["id"],
                    "source_title":     r["source_title"],
                    "source_url":       r.get("source_url", ""),
                    "witness_citation": {
                        "author":       r.get("citation_author", ""),
                        "year":         r.get("citation_year"),
                        "archive_name": r.get("citation_archive_name", ""),
                    },
                    "similarity_score": float(r["similarity_score"]),
                    "verdict":          "VERIFIED",
                    "chunk":            r["chunk"],
                } for r in reference_chunks],
                "is_silenced":      False,
                "homestead_content": None,
            })
        else:
            # No Hippocampus content — Claude generates from its own literary knowledge
            content = await _synthesize_literature(
                request=request,
                book_title=None,
                book_author=None,
                topic=request.topic,
            )
            blocks.append({
                "block_type":       BlockType.NARRATIVE.value,
                "content":          _worldview_wrap(content, request.track),
                "evidence":         [],
                "is_silenced":      False,
                "homestead_content": None,
            })

    # ── Multimodal synthesis ─────────────────────────────────────────────────
    await _run_multimodal_synthesis(state, blocks)

    state["blocks"] = blocks
    return state


async def _synthesize_literature(
    request: LessonRequest,
    book_title: str | None,
    book_author: str | None,
    topic: str,
) -> str:
    """
    Claude generates literary analysis content.
    If a specific book is provided, the analysis is grounded in that text.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        if book_title:
            return f"Literary analysis of '{topic}' in the context of *{book_title}* by {book_author}."
        return f"Literary analysis: {topic}"

    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    persona = _TRACK_PERSONA.get(Track.ENGLISH_LITERATURE, "a literary mentor")

    if book_title:
        user_prompt = (
            f"The student is currently reading *{book_title}* by {book_author}.\n\n"
            f"Topic they asked about: {topic}\n\n"
            f"Write a literary analysis that connects this topic to the book they're reading. "
            f"Discuss themes, character choices, narrative technique, or author's intent. "
            f"Make the student think critically about what they're reading."
        )
    else:
        user_prompt = (
            f"Topic: {topic}\n\n"
            f"Write a literary analysis or discussion of this topic. "
            f"Reference specific works, authors, or literary movements where relevant. "
            f"Make the student think critically about stories, language, and meaning."
        )

    system_prompt = (
        f"You are Adeline — {persona}\n\n"
        f"You are writing for a {grade_desc} student in a Christian homeschool family.\n\n"
        f"{_ADELINE_VOICE}\n"
        "CONTENT RULES:\n"
        "• 2-3 paragraphs maximum\n"
        "• Discuss the text as literature — themes, craft, truth claims, worldview\n"
        "• Do NOT try to fact-check fiction. Analyze it.\n"
        "• End with a question that makes the student think about what the author is really saying\n"
    )

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"[LiteratureAgent] Claude synthesis failed: {e}")
        if book_title:
            return f"Literary analysis of '{topic}' in the context of *{book_title}* by {book_author}."
        return f"Literary analysis: {topic}"


# ── Practical Agent (APPLIED_MATHEMATICS, CREATIVE_ECONOMY) ──────────────────

async def practical_agent(state: AdelineState) -> AdelineState:
    """
    Practical skills specialist — math, making, and business.

    Does NOT use the Witness Protocol. These tracks teach applied skills,
    not historical truth claims. A compound interest formula doesn't need
    a cosine similarity score.

    Uses Hippocampus as reference material (if available) without gating
    on similarity threshold. When Hippocampus is empty, Claude generates
    practical content from its knowledge.
    """
    request = state["request"]
    state["agent_name"] = "PracticalAgent"
    blocks: list[dict] = []

    # Pull any Hippocampus content as reference (no Witness gate)
    raw_results = await hippocampus.similarity_search(
        query_embedding=state["query_embedding"],
        track=request.track.value,
        top_k=3,
    )

    if raw_results:
        # Use Hippocampus results as reference material for synthesis
        content = await _synthesize_content(
            request=request,
            block_type=BlockType.NARRATIVE.value,
            source_chunks=raw_results,
            raw_content=raw_results[0]["chunk"],
        )
        blocks.append({
            "block_type":       BlockType.NARRATIVE.value,
            "content":          _worldview_wrap(content, request.track),
            "evidence":         [{
                "source_id":        r["id"],
                "source_title":     r["source_title"],
                "source_url":       r.get("source_url", ""),
                "witness_citation": {
                    "author":       r.get("citation_author", ""),
                    "year":         r.get("citation_year"),
                    "archive_name": r.get("citation_archive_name", ""),
                },
                "similarity_score": float(r["similarity_score"]),
                "verdict":          "VERIFIED",
                "chunk":            r["chunk"],
            } for r in raw_results],
            "is_silenced":      False,
            "homestead_content": (
                _homestead_adapt(raw_results[0]["chunk"]) if request.is_homestead else None
            ),
        })
    else:
        # No Hippocampus content — Claude generates practical content
        content = await _synthesize_practical(request)
        blocks.append({
            "block_type":       BlockType.NARRATIVE.value,
            "content":          _worldview_wrap(content, request.track),
            "evidence":         [],
            "is_silenced":      False,
            "homestead_content": None,
        })

    # ── Multimodal synthesis ─────────────────────────────────────────────────
    await _run_multimodal_synthesis(state, blocks)

    state["blocks"] = blocks
    return state


async def _synthesize_practical(request: LessonRequest) -> str:
    """Claude generates practical/applied content for math and creative economy."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return f"Practical lesson: {request.topic}"

    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    persona = _TRACK_PERSONA.get(request.track, "a practical mentor")

    system_prompt = (
        f"You are Adeline — {persona}\n\n"
        f"You are writing for a {grade_desc} student in a Christian homeschool family.\n\n"
        f"{_ADELINE_VOICE}\n"
        "CONTENT RULES:\n"
        "• 2-3 paragraphs maximum\n"
        "• Use REAL numbers, REAL scenarios, REAL materials\n"
        "• Every lesson must end with something the student can DO or CALCULATE today\n"
        "• No abstract theory without a concrete application\n"
        "• If math: show the formula, then a worked example using their life\n"
        "• If creative economy: name a specific product, pricing strategy, or skill to practice\n"
    )

    user_prompt = (
        f"Topic: {request.topic}\n"
        f"Track: {request.track.value.replace('_', ' ').title()}\n\n"
        f"Write a practical lesson in Adeline's voice. Ground it in something real "
        f"the student can do this week."
    )

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"[PracticalAgent] Claude synthesis failed: {e}")
        return f"Practical lesson: {request.topic}"


# ── Format selector ───────────────────────────────────────────────────────────

async def _decide_formats(
    topic: str,
    content: str,
    track: "Track",
    grade_level: str,
    allow_timeline: bool = False,
) -> list[str]:
    """
    One Claude call decides which multimodal formats genuinely add value
    for this specific lesson. Returns a subset of the available formats.

    Rules Claude uses:
    - MIND_MAP: good for multi-concept topics; skip for single ideas or stories
    - TIMELINE: only if chronology is present AND allow_timeline=True
    - MNEMONIC: only if 3+ distinct terms need to be memorised
    - NARRATED_SLIDE: good for most lessons; skip if content is very short (<150 chars)
    """
    import json as _json

    if not os.getenv("ANTHROPIC_API_KEY"):
        # Fallback: return sensible defaults without Claude
        defaults = ["MIND_MAP", "NARRATED_SLIDE"]
        if allow_timeline:
            defaults.insert(1, "TIMELINE")
        return defaults

    available = ["MIND_MAP", "MNEMONIC", "NARRATED_SLIDE"]
    if allow_timeline:
        available.insert(1, "TIMELINE")

    grade_desc = _GRADE_DESC.get(grade_level, f"grade {grade_level}")

    system_prompt = (
        "You are a curriculum designer deciding which learning formats add genuine value "
        "to a specific lesson. Be selective — clutter hurts learning. "
        "Output ONLY valid JSON: {\"formats\": [\"FORMAT1\", ...]}"
    )
    user_prompt = (
        f"Lesson topic: {topic}\n"
        f"Track: {track.value.replace('_', ' ')}\n"
        f"Grade: {grade_desc}\n"
        f"Content preview: {content[:400]}\n\n"
        f"Available formats: {available}\n\n"
        "Which formats genuinely add learning value for THIS specific lesson?\n"
        "Rules:\n"
        "- MIND_MAP: include if the topic has multiple related concepts with hierarchy. "
        "Skip for single-concept topics or narrative stories.\n"
        "- TIMELINE: include only if chronological sequence is central to the topic.\n"
        "- MNEMONIC: include only if there are 3+ distinct terms/facts the student must memorise.\n"
        "- NARRATED_SLIDE: include for most lessons. Skip only if content is a single short paragraph.\n"
        "Return 0-3 formats maximum. Be honest — fewer is better than irrelevant blocks."
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = await client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=100,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = message.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        raw = _json.loads(text)
        chosen = [f for f in raw.get("formats", []) if f in available]
        logger.info(f"[FormatSelector] Chose {chosen} for '{topic}' ({track.value})")
        return chosen
    except Exception as e:
        logger.warning(f"[FormatSelector] Failed — using defaults: {e}")
        return ["MIND_MAP", "NARRATED_SLIDE"]


async def _run_multimodal_synthesis(
    state: "AdelineState",
    blocks: list[dict],
    allow_timeline: bool = False,
    is_seasonal_timeline: bool = False,
) -> None:
    """
    Decide which formats add value, then run only those synthesis functions.
    Appends new blocks to the blocks list in-place.
    """
    if not blocks:
        return

    request = state["request"]
    primary_content = blocks[0].get("content", "")
    parent_evidence = blocks[0].get("evidence", [])

    formats = await _decide_formats(
        topic=request.topic,
        content=primary_content,
        track=request.track,
        grade_level=request.grade_level,
        allow_timeline=allow_timeline,
    )

    if "MIND_MAP" in formats:
        mm = await _synthesize_mind_map(request.topic, primary_content, request.grade_level)
        if mm:
            blocks.append({
                "block_type": BlockType.MIND_MAP.value,
                "content": f"Concept map: {mm.concept}",
                "evidence": [],
                "is_silenced": False,
                "homestead_content": None,
                "mind_map_data": mm.model_dump(),
            })

    if "TIMELINE" in formats:
        tl = await _synthesize_timeline(
            request.topic, primary_content, parent_evidence,
            request.grade_level, is_seasonal=is_seasonal_timeline,
        )
        if tl:
            label = "Seasonal calendar" if is_seasonal_timeline else "Timeline"
            blocks.append({
                "block_type": BlockType.TIMELINE.value,
                "content": f"{label}: {tl.span}",
                "evidence": parent_evidence if not is_seasonal_timeline else [],
                "is_silenced": False,
                "homestead_content": None,
                "timeline_data": tl.model_dump(),
            })

    if "MNEMONIC" in formats:
        mn = await _synthesize_mnemonic(primary_content, request.grade_level)
        if mn:
            blocks.append({
                "block_type": BlockType.MNEMONIC.value,
                "content": f"Remember: {mn.acronym} — {mn.concept}",
                "evidence": [],
                "is_silenced": False,
                "homestead_content": None,
                "mnemonic_data": mn.model_dump(),
            })

    if "NARRATED_SLIDE" in formats:
        ns = await _synthesize_narrated_slide(
            request.topic, primary_content, request.track, request.grade_level
        )
        if ns:
            blocks.append({
                "block_type": BlockType.NARRATED_SLIDE.value,
                "content": f"{len(ns.slides)} slides · {ns.total_duration_minutes} min",
                "evidence": [],
                "is_silenced": False,
                "homestead_content": None,
                "narrated_slide_data": ns.model_dump(),
            })


# ── Multimodal synthesis functions ────────────────────────────────────────────

async def _synthesize_mind_map(
    topic: str,
    content: str,
    grade_level: str,
) -> "MindMapData | None":
    """
    Extract a concept hierarchy from lesson content.
    Returns None on any failure — never surfaces errors to the student.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    from app.schemas.api_models import MindMapData
    import json

    grade_desc = _GRADE_DESC.get(grade_level, f"grade {grade_level}")
    system_prompt = (
        "You extract concept hierarchies from lesson content. "
        "Output ONLY valid JSON — no prose, no markdown fences. "
        "Format: {\"concept\": \"<central topic>\", \"root\": {\"id\": \"<uuid>\", \"label\": \"<root label>\", \"children\": [...]}}\n"
        "Rules: max 3 levels deep, max 4 children per node. Each node has id (uuid string), label (short phrase), children (array)."
    )
    user_prompt = (
        f"Lesson topic: {topic}\n"
        f"Student grade: {grade_desc}\n\n"
        f"Content:\n{content[:2000]}\n\n"
        "Extract the concept hierarchy as JSON."
    )
    try:
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = await client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return MindMapData.model_validate(json.loads(message.content[0].text))
    except Exception as e:
        logger.warning(f"[MindMap] synthesis failed: {e}")
        return None


async def _synthesize_timeline(
    topic: str,
    content: str,
    evidence: list,
    grade_level: str,
    is_seasonal: bool = False,
) -> "TimelineData | None":
    """
    Extract a chronological sequence from lesson content.
    For history tracks: maps events to source_title from evidence.
    For homesteading: generates a seasonal calendar.
    Returns None on any failure.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    from app.schemas.api_models import TimelineData
    import json

    grade_desc = _GRADE_DESC.get(grade_level, f"grade {grade_level}")
    source_titles = [e.get("source_title", "") for e in evidence if isinstance(e, dict)]
    source_context = f"Available primary sources: {', '.join(source_titles)}" if source_titles else ""

    if is_seasonal:
        system_prompt = (
            "You create seasonal homesteading calendars. "
            "Output ONLY valid JSON — no prose, no markdown fences. "
            "Format: {\"span\": \"<year or season range>\", \"events\": [{\"date\": \"<season>\", \"label\": \"<task>\", \"description\": \"<1-2 sentences>\", \"source_title\": \"\"}]}"
        )
        user_prompt = f"Create a seasonal homesteading calendar for: {topic}\n\nContent:\n{content[:1500]}"
    else:
        system_prompt = (
            "You extract chronological events from history lesson content. "
            "Output ONLY valid JSON — no prose, no markdown fences. "
            "Format: {\"span\": \"<year range e.g. 1860-1870>\", \"events\": [{\"date\": \"<year or date>\", \"label\": \"<short title>\", \"description\": \"<1-2 sentences>\", \"source_title\": \"<from available sources or empty>\"}]}\n"
            "Use consistent date format within the timeline. 4-8 events maximum."
        )
        user_prompt = (
            f"Lesson topic: {topic}\n"
            f"Student grade: {grade_desc}\n"
            f"{source_context}\n\n"
            f"Content:\n{content[:2000]}\n\n"
            "Extract the chronological timeline as JSON."
        )
    try:
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = await client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return TimelineData.model_validate(json.loads(message.content[0].text))
    except Exception as e:
        logger.warning(f"[Timeline] synthesis failed: {e}")
        return None


async def _synthesize_mnemonic(
    content: str,
    grade_level: str,
) -> "MnemonicData | None":
    """
    Generate a mnemonic device when ≥3 concepts are present in the content.
    Returns None if fewer than 3 concepts detected or on any failure.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    from app.schemas.api_models import MnemonicData
    import json

    grade_desc = _GRADE_DESC.get(grade_level, f"grade {grade_level}")
    system_prompt = (
        "You create educational mnemonic devices. "
        "First, check if the content introduces 3 or more distinct concepts or terms. "
        "If fewer than 3, respond with exactly: {\"skip\": true}\n"
        "If 3 or more, output ONLY valid JSON — no prose, no markdown fences. "
        "Format: {\"concept\": \"<what it helps remember>\", \"acronym\": \"<WORD>\", \"words\": [\"<word1>\", \"<word2>\", ...], \"tip\": \"<memorable sentence>\"}\n"
        "CRITICAL: len(words) MUST equal len(acronym). One word per letter."
    )
    user_prompt = (
        f"Student grade: {grade_desc}\n\n"
        f"Content:\n{content[:1500]}\n\n"
        "Create a mnemonic device for the key concepts in this content."
    )
    try:
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = await client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=400,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = json.loads(message.content[0].text)
        if raw.get("skip"):
            return None
        return MnemonicData.model_validate(raw)
    except Exception as e:
        logger.warning(f"[Mnemonic] synthesis failed: {e}")
        return None


async def _synthesize_narrated_slide(
    topic: str,
    content: str,
    track: "Track",
    grade_level: str,
) -> "NarratedSlideData | None":
    """
    Convert lesson content into a 3-5 slide narrated presentation.
    Returns None on any failure.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    from app.schemas.api_models import NarratedSlideData
    import json

    grade_desc = _GRADE_DESC.get(grade_level, f"grade {grade_level}")
    system_prompt = (
        "You convert lesson content into narrated slide decks for students. "
        "Output ONLY valid JSON — no prose, no markdown fences. "
        "Format: {\"total_duration_minutes\": <float>, \"slides\": [{\"slide_number\": <int starting at 1>, \"title\": \"<title>\", \"bullets\": [\"<bullet1>\", \"<bullet2>\"], \"narration\": \"<30-60 second spoken script>\"}]}\n"
        "Rules: 3-5 slides, 2-4 bullets per slide, narration is natural spoken language (not bullet points)."
    )
    user_prompt = (
        f"Lesson topic: {topic}\n"
        f"Student grade: {grade_desc}\n\n"
        f"Content:\n{content[:2000]}\n\n"
        "Convert this into a narrated slide deck."
    )
    try:
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = await client.messages.create(
            model=_ANTHROPIC_MODEL,
            max_tokens=1200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return NarratedSlideData.model_validate(json.loads(message.content[0].text))
    except Exception as e:
        logger.warning(f"[NarratedSlide] synthesis failed: {e}")
        return None


# ── Discipleship Agent ─────────────────────────────────────────────────────────
# Covers: HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP
# (ENGLISH_LITERATURE → literature_agent, APPLIED_MATH/CREATIVE_ECONOMY → practical_agent)

async def discipleship_agent(state: AdelineState) -> AdelineState:
    """
    Worldview, Character, and Cultural Discernment specialist.
    Covers HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP.

    Produces NARRATIVE blocks that weave source material into a worldview-aligned
    framing (scripture context, character formation, cultural discernment).
    VERIFIED sources are presented with interpretive narrative wrap.
    ARCHIVE_SILENT: tries Researcher; falls back to RESEARCH_MISSION.

    Sefaria integration: Detects biblical references and fetches
    Everett Fox translation from Sefaria API.
    """
    request = state["request"]
    state["agent_name"] = "DiscipleshipAgent"
    blocks: list[dict] = []

    # Check for biblical references in topic (Sefaria integration)
    from app.services.sefaria import detect_biblical_reference, fetch_biblical_text, format_sefaria_content

    biblical_ref = detect_biblical_reference(request.topic)

    if biblical_ref:
        logger.info(f"[DiscipleshipAgent] Detected biblical reference: {biblical_ref}")
        sefaria_data = await fetch_biblical_text(biblical_ref)

        if sefaria_data:
            content = format_sefaria_content(sefaria_data, request.grade_level)

            blocks.append({
                "block_type": BlockType.NARRATIVE.value,
                "content": _worldview_wrap(content, request.track),
                "evidence": [{
                    "source_id": f"sefaria-{biblical_ref}",
                    "source_title": f"{sefaria_data['ref']} ({sefaria_data['version_title']})",
                    "source_url": sefaria_data['url'],
                    "witness_citation": {
                        "author": "Everett Fox (Translator)" if sefaria_data['is_fox'] else "Sefaria.org",
                        "year": 1995 if sefaria_data['is_fox'] else None,
                        "archive_name": "Sefaria / Schocken Books" if sefaria_data['is_fox'] else "Sefaria.org",
                    },
                    "similarity_score": 1.0,
                    "verdict": "VERIFIED",
                    "chunk": sefaria_data['english'],
                }],
                "is_silenced": False,
            })

            # Fall through to multimodal synthesis below
        else:
            logger.warning(f"[DiscipleshipAgent] Failed to fetch {biblical_ref} from Sefaria, falling back to Hippocampus")

    # Hippocampus reference — no Witness Protocol threshold.
    # Discipleship content is worldview synthesis, not archival verification.
    # Hippocampus results are context; Claude wraps them in Adeline's voice.
    raw_results = await hippocampus.similarity_search(
        query_embedding=state["query_embedding"],
        track=request.track.value,
        top_k=3,
    )

    for result in raw_results:
        raw = result["chunk"]
        content = await _synthesize_content(
            request=request,
            block_type=BlockType.NARRATIVE.value,
            source_chunks=[result],
            raw_content=raw,
        )
        blocks.append({
            "block_type":        BlockType.NARRATIVE.value,
            "content":           _worldview_wrap(content, request.track),
            "evidence":          [{
                "source_id":        result["id"],
                "source_title":     result["source_title"],
                "source_url":       result.get("source_url", ""),
                "witness_citation": {
                    "author":       result.get("citation_author", ""),
                    "year":         result.get("citation_year"),
                    "archive_name": result.get("citation_archive_name", ""),
                },
                "similarity_score": float(result["similarity_score"]),
                "verdict":          "VERIFIED",
                "chunk":            raw,
            }],
            "is_silenced":       False,
            "homestead_content": _homestead_adapt(raw) if request.is_homestead else None,
        })

    if not blocks:
        # Hippocampus empty — try web search first (seeds Hippocampus for next time)
        logger.info("[DiscipleshipAgent] Hippocampus empty — searching web to seed and generate.")
        web_results = await search_witnesses(request.topic, request.track.value)
        if web_results:
            raw = web_results[0].get("chunk", request.topic)
            content = await _synthesize_content(
                request=request,
                block_type=BlockType.NARRATIVE.value,
                source_chunks=web_results,
                raw_content=raw,
            )
            blocks.append({
                "block_type":        BlockType.NARRATIVE.value,
                "content":           _worldview_wrap(content, request.track),
                "evidence":          [{
                    "source_id":        r.get("source_id", ""),
                    "source_title":     r.get("source_title", ""),
                    "source_url":       r.get("source_url", ""),
                    "witness_citation": r.get("witness_citation", {}),
                    "similarity_score": float(r.get("similarity_score", 0)),
                    "verdict":          "VERIFIED",
                    "chunk":            r.get("chunk", ""),
                } for r in web_results[:2]],
                "is_silenced":       False,
                "homestead_content": None,
            })
            state["researcher_activated"] = True
        else:
            # Web search also empty — Claude generates from its own knowledge
            logger.info("[DiscipleshipAgent] No web results — generating from Claude knowledge.")
            content = await _synthesize_content(
                request=request,
                block_type=BlockType.NARRATIVE.value,
                source_chunks=[],
                raw_content=request.topic,
            )
            blocks.append({
                "block_type":        BlockType.NARRATIVE.value,
                "content":           _worldview_wrap(content, request.track),
                "evidence":          [],
                "is_silenced":       False,
                "homestead_content": None,
            })

    # ── Multimodal synthesis ─────────────────────────────────────────────────
    await _run_multimodal_synthesis(state, blocks)

    state["blocks"] = blocks
    return state


def _worldview_wrap(content: str, track: Track) -> str:
    """
    Frame content with a plain-spoken worldview lens per track.
    No churchy clichés. No hollow motivation. Just truth, connected to purpose.
    """
    lead = {
        Track.DISCIPLESHIP:         "Scripture doesn't stop at Sunday morning.",
        Track.HEALTH_NATUROPATHY:   "Your body was designed by YHWH — not by Pfizer.",
        Track.GOVERNMENT_ECONOMICS: "Power doesn't work the way the textbook says.",
        Track.ENGLISH_LITERATURE:   "Every story is a truth claim. Read it like one.",
        Track.APPLIED_MATHEMATICS:  "Math doesn't live on tests. It lives on your land, in your budget, at the market.",
        Track.CREATIVE_ECONOMY:     "Making something with your hands that someone will pay for is one of the most countercultural things you can do.",
    }.get(track, "Here's what this actually means:")

    # The closing challenge replaces the generic "How does this shape..." question
    challenge = {
        Track.DISCIPLESHIP:         "What does Scripture actually say about this — and what does that require of you?",
        Track.HEALTH_NATUROPATHY:   "What would you do differently if you trusted your body more than the system?",
        Track.JUSTICE_CHANGEMAKING:  "Corporations do this for profit. How would you do it for justice?",
        Track.GOVERNMENT_ECONOMICS: "Who benefits from this system staying broken? Who pays the price?",
        Track.ENGLISH_LITERATURE:   "What does this author want you to believe — and do you agree?",
        Track.APPLIED_MATHEMATICS:  "Where would you use this math this week? Calculate a real number.",
        Track.CREATIVE_ECONOMY:     "What will you make? What materials do you already have? What would you charge for it?",
    }.get(track, "What does this change about how you act?")

    return (
        f"*{lead}*\n\n"
        f"{content}\n\n"
        f"*{challenge}*"
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
    verified_count   = sum(
        1 for b in blocks
        if b.get("block_type") in (BlockType.PRIMARY_SOURCE.value, BlockType.NARRATIVE.value)
    )
    lab_count        = sum(1 for b in blocks if b.get("block_type") == BlockType.LAB_MISSION.value)
    experiment_count = sum(1 for b in blocks if b.get("block_type") == BlockType.EXPERIMENT.value)
    mindmap_count    = sum(1 for b in blocks if b.get("block_type") == BlockType.MIND_MAP.value)
    timeline_count   = sum(1 for b in blocks if b.get("block_type") == BlockType.TIMELINE.value)
    mnemonic_count   = sum(1 for b in blocks if b.get("block_type") == BlockType.MNEMONIC.value)
    slide_count      = sum(1 for b in blocks if b.get("block_type") == BlockType.NARRATED_SLIDE.value)
    credit_hours     = round(min(1.0,
        0.1  * (verified_count + lab_count) +
        0.25 * experiment_count +
        0.05 * (mindmap_count + timeline_count) +
        0.03 * mnemonic_count +
        0.08 * slide_count
    ), 2)

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
            + (f", {experiment_count} experiment(s)" if experiment_count else "")
            + (f", {mindmap_count + timeline_count} visual map(s)" if mindmap_count + timeline_count else "")
            + (f", {slide_count} slide deck(s)" if slide_count else "")
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
        BlockType.EXPERIMENT.value:       "completed",    # Sovereign Lab experiments count as "completed"
        BlockType.RESEARCH_MISSION.value: "interacted",
        BlockType.QUIZ.value:             "attempted",
        BlockType.TEXT.value:             "experienced",
        BlockType.MIND_MAP.value:       "composed",
        BlockType.TIMELINE.value:       "experienced",
        BlockType.MNEMONIC.value:       "memorized",
        BlockType.NARRATED_SLIDE.value: "experienced",
    }.get(block_type, "experienced")


def _track_to_credit_type(track: Track) -> str:
    """
    Map track to default credit type.
    CREATION_SCIENCE now returns LABORATORY_SCIENCE (not generic CORE)
    when the lesson contains EXPERIMENT blocks — handled in registrar_agent.
    """
    return {
        Track.TRUTH_HISTORY:        "CORE",
        Track.CREATION_SCIENCE:     "LABORATORY_SCIENCE",
        Track.ENGLISH_LITERATURE:   "CORE",
        Track.GOVERNMENT_ECONOMICS: "CORE",
        Track.JUSTICE_CHANGEMAKING: "CORE",
        Track.DISCIPLESHIP:         "ELECTIVE",
        Track.HEALTH_NATUROPATHY:   "ELECTIVE",
        Track.HOMESTEADING:         "HOMESTEAD",
        Track.APPLIED_MATHEMATICS:  "MATHEMATICS",
        Track.CREATIVE_ECONOMY:     "VOCATIONAL",
    }.get(track, "ELECTIVE")


# ── Router ────────────────────────────────────────────────────────────────────

def _route(state: AdelineState) -> Literal[
    "historian", "justice", "science", "discipleship", "literature", "practical"
]:
    track = state["request"].track
    if track in _HISTORIAN_TRACKS:
        return "historian"
    if track in _JUSTICE_TRACKS:
        return "justice"
    if track in _SCIENCE_TRACKS:
        return "science"
    if track in _LITERATURE_TRACKS:
        return "literature"
    if track in _PRACTICAL_TRACKS:
        return "practical"
    return "discipleship"


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def run_orchestrator(
    request: LessonRequest,
    query_embedding: list[float],
    interaction_count: int = 10,
    cross_track_acknowledgment: str | None = None,
) -> LessonResponse:
    """
    Routes the request to the correct specialist agent, graph-links to
    OAS Standards via Neo4j, runs the RegistrarAgent for xAPI + CASE credits,
    and returns a structured LessonResponse.

    Agent routing:
      TRUTH_HISTORY                          → HistorianAgent (Witness Protocol 0.82)
      JUSTICE_CHANGEMAKING                   → JusticeAgent (power-capture framing)
      CREATION_SCIENCE, HOMESTEADING         → ScienceAgent (LAB_MISSION)
      ENGLISH_LITERATURE                     → LiteratureAgent (book-context, no Witness)
      APPLIED_MATHEMATICS, CREATIVE_ECONOMY  → PracticalAgent (applied skills, no Witness)
      HEALTH_NATUROPATHY, GOV_ECON, DISCIP.  → DiscipleshipAgent (worldview + Witness)

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
        "interaction_count":    interaction_count,
        "cross_track_acknowledgment": cross_track_acknowledgment,
    }

    route = _route(state)
    logger.info(
        f"[Orchestrator] Routing to: {route} | "
        f"track={request.track.value} | topic='{request.topic}'"
    )

    # ── 1. Specialist agent ────────────────────────────────────────────────────
    if route == "historian":
        state = await historian_agent(state)
    elif route == "justice":
        state = await justice_agent(state)
    elif route == "science":
        state = await science_agent(state)
    elif route == "literature":
        state = await literature_agent(state)
    elif route == "practical":
        state = await practical_agent(state)
    else:
        state = await discipleship_agent(state)

    # ── 2. Cross-track acknowledgment (prepend to first block if set) ─────────
    if state.get("cross_track_acknowledgment") and state["blocks"]:
        state["blocks"][0]["content"] = (
            state["cross_track_acknowledgment"] + "\n\n" + state["blocks"][0]["content"]
        )

    # ── 3. Graph context (Neo4j) ───────────────────────────────────────────────
    state["oas_standards"] = await _fetch_graph_context(request.track.value)
    primary_count = sum(1 for s in state["oas_standards"] if s.get("source_type") == "primary")
    cross_count   = sum(1 for s in state["oas_standards"] if s.get("source_type") == "cross_track")

    # ── 4. Registrar (xAPI + CASE credits) ────────────────────────────────────
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
