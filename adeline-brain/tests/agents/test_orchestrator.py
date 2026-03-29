"""
Unit tests for adeline-brain/app/agents/orchestrator.py

Tests cover:
  - _route() dispatches to correct agent per track
  - registrar_agent() emits correct xAPI statements and CASE credits
  - _block_type_to_xapi_verb() mapping
  - _track_to_credit_type() mapping
  - _worldview_wrap() framing per track
  - Full run_orchestrator() with mocked Hippocampus + Neo4j + Researcher

Heavy IO paths (Hippocampus, Neo4j, Researcher) are fully mocked so tests
run without any external connections.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.schemas.api_models import (
    LessonRequest, Track, BlockType, EvidenceVerdict, Evidence, WitnessCitation,
)
from app.agents.orchestrator import (
    AdelineState,
    _route,
    _block_type_to_xapi_verb,
    _track_to_credit_type,
    _worldview_wrap,
    _homestead_adapt,
    registrar_agent,
    run_orchestrator,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_request(track: Track = Track.TRUTH_HISTORY, is_homestead: bool = False) -> LessonRequest:
    return LessonRequest(
        student_id="stu-001",
        track=track,
        topic="soil pH and crop yields",
        is_homestead=is_homestead,
        grade_level="7",
    )


def _make_state(track: Track = Track.TRUTH_HISTORY, blocks: list | None = None) -> AdelineState:
    return AdelineState(
        request=_make_request(track),
        lesson_id="lesson-test-001",
        query_embedding=[0.1] * 1536,
        blocks=blocks or [],
        oas_standards=[{"standard_id": "OK-SC-7.4", "source_type": "primary"}],
        has_research_missions=False,
        researcher_activated=False,
        agent_name="",
        xapi_statements=[],
        credits_awarded=[],
    )


# ── _route() ──────────────────────────────────────────────────────────────────

class TestRoute:
    def test_truth_history_routes_to_historian(self):
        state = _make_state(Track.TRUTH_HISTORY)
        assert _route(state) == "historian"

    def test_justice_changemaking_routes_to_historian(self):
        state = _make_state(Track.JUSTICE_CHANGEMAKING)
        assert _route(state) == "historian"

    def test_creation_science_routes_to_science(self):
        state = _make_state(Track.CREATION_SCIENCE)
        assert _route(state) == "science"

    def test_homesteading_routes_to_science(self):
        state = _make_state(Track.HOMESTEADING)
        assert _route(state) == "science"

    def test_discipleship_routes_to_discipleship(self):
        state = _make_state(Track.DISCIPLESHIP)
        assert _route(state) == "discipleship"

    def test_health_routes_to_discipleship(self):
        state = _make_state(Track.HEALTH_NATUROPATHY)
        assert _route(state) == "discipleship"

    def test_government_routes_to_discipleship(self):
        state = _make_state(Track.GOVERNMENT_ECONOMICS)
        assert _route(state) == "discipleship"

    def test_english_routes_to_discipleship(self):
        state = _make_state(Track.ENGLISH_LITERATURE)
        assert _route(state) == "discipleship"


# ── _block_type_to_xapi_verb() ────────────────────────────────────────────────

class TestBlockTypeToVerb:
    def test_primary_source_is_experienced(self):
        assert _block_type_to_xapi_verb(BlockType.PRIMARY_SOURCE.value) == "experienced"

    def test_narrative_is_experienced(self):
        assert _block_type_to_xapi_verb(BlockType.NARRATIVE.value) == "experienced"

    def test_lab_mission_is_attempted(self):
        assert _block_type_to_xapi_verb(BlockType.LAB_MISSION.value) == "attempted"

    def test_research_mission_is_interacted(self):
        assert _block_type_to_xapi_verb(BlockType.RESEARCH_MISSION.value) == "interacted"

    def test_unknown_falls_back_to_experienced(self):
        assert _block_type_to_xapi_verb("UNKNOWN_TYPE") == "experienced"


# ── _track_to_credit_type() ───────────────────────────────────────────────────

class TestTrackToCreditType:
    def test_truth_history_is_core(self):
        assert _track_to_credit_type(Track.TRUTH_HISTORY) == "CORE"

    def test_creation_science_is_core(self):
        assert _track_to_credit_type(Track.CREATION_SCIENCE) == "CORE"

    def test_homesteading_is_homestead(self):
        assert _track_to_credit_type(Track.HOMESTEADING) == "HOMESTEAD"

    def test_discipleship_is_elective(self):
        assert _track_to_credit_type(Track.DISCIPLESHIP) == "ELECTIVE"

    def test_health_is_elective(self):
        assert _track_to_credit_type(Track.HEALTH_NATUROPATHY) == "ELECTIVE"


# ── _worldview_wrap() ─────────────────────────────────────────────────────────

class TestWorldviewWrap:
    def test_discipleship_track_uses_biblical_lens(self):
        result = _worldview_wrap("Some content here.", Track.DISCIPLESHIP)
        assert "biblical worldview" in result
        assert "Some content here." in result

    def test_health_track_uses_body_design_lens(self):
        result = _worldview_wrap("Herbs help the body.", Track.HEALTH_NATUROPATHY)
        assert "God designed the body" in result

    def test_wrap_includes_reflection_prompt(self):
        result = _worldview_wrap("Content.", Track.ENGLISH_LITERATURE)
        assert "God's design" in result or "calling" in result


# ── registrar_agent() ─────────────────────────────────────────────────────────

class TestRegistrarAgent:
    @pytest.mark.asyncio
    async def test_emits_one_xapi_statement_per_block(self):
        blocks = [
            {"block_type": BlockType.PRIMARY_SOURCE.value, "content": "Block 1"},
            {"block_type": BlockType.NARRATIVE.value, "content": "Block 2"},
        ]
        state = _make_state(Track.TRUTH_HISTORY, blocks=blocks)
        state["agent_name"] = "HistorianAgent"

        result = await registrar_agent(state)

        assert len(result["xapi_statements"]) == 2

    @pytest.mark.asyncio
    async def test_xapi_statement_has_required_fields(self):
        blocks = [{"block_type": BlockType.LAB_MISSION.value, "content": "Lab"}]
        state = _make_state(Track.HOMESTEADING, blocks=blocks)
        state["agent_name"] = "ScienceAgent"

        result = await registrar_agent(state)

        stmt = result["xapi_statements"][0]
        assert "id" in stmt
        assert "actor" in stmt
        assert "verb" in stmt
        assert "object" in stmt
        assert "context" in stmt
        assert stmt["verb"]["display"]["en-US"] == "attempted"

    @pytest.mark.asyncio
    async def test_xapi_context_contains_track_and_agent(self):
        blocks = [{"block_type": BlockType.PRIMARY_SOURCE.value, "content": "c"}]
        state = _make_state(Track.HOMESTEADING, blocks=blocks)
        state["agent_name"] = "ScienceAgent"

        result = await registrar_agent(state)

        ext = result["xapi_statements"][0]["context"]["extensions"]
        assert ext["https://adeline.app/xapi/ext/track"] == "HOMESTEADING"
        assert ext["https://adeline.app/xapi/ext/agent"] == "ScienceAgent"

    @pytest.mark.asyncio
    async def test_emits_one_case_credit_entry(self):
        blocks = [{"block_type": BlockType.PRIMARY_SOURCE.value, "content": "c"}]
        state = _make_state(Track.TRUTH_HISTORY, blocks=blocks)
        state["agent_name"] = "HistorianAgent"

        result = await registrar_agent(state)

        assert len(result["credits_awarded"]) == 1

    @pytest.mark.asyncio
    async def test_homesteading_credit_type_is_homestead(self):
        blocks = [{"block_type": BlockType.LAB_MISSION.value, "content": "lab"}]
        state = _make_state(Track.HOMESTEADING, blocks=blocks)
        state["agent_name"] = "ScienceAgent"

        result = await registrar_agent(state)

        credit = result["credits_awarded"][0]
        assert credit["credit_type"] == "HOMESTEAD"

    @pytest.mark.asyncio
    async def test_credit_hours_scale_with_verified_blocks(self):
        blocks = [
            {"block_type": BlockType.PRIMARY_SOURCE.value, "content": "c1"},
            {"block_type": BlockType.PRIMARY_SOURCE.value, "content": "c2"},
            {"block_type": BlockType.RESEARCH_MISSION.value, "content": "r"},
        ]
        state = _make_state(Track.TRUTH_HISTORY, blocks=blocks)
        state["agent_name"] = "HistorianAgent"

        result = await registrar_agent(state)

        credit = result["credits_awarded"][0]
        # 2 verified × 0.1 = 0.2, capped at 1.0
        assert credit["credit_hours"] == 0.2

    @pytest.mark.asyncio
    async def test_credit_hours_capped_at_one(self):
        blocks = [
            {"block_type": BlockType.PRIMARY_SOURCE.value, "content": f"c{i}"}
            for i in range(15)
        ]
        state = _make_state(Track.TRUTH_HISTORY, blocks=blocks)
        state["agent_name"] = "HistorianAgent"

        result = await registrar_agent(state)

        assert result["credits_awarded"][0]["credit_hours"] == 1.0


# ── run_orchestrator() integration (mocked IO) ────────────────────────────────

_FAKE_EVIDENCE = {
    "id":                "ev-001",
    "source_title":      "Oklahoma History Primer",
    "source_url":        "https://archive.org/ok-primer",
    "citation_author":   "J. Smith",
    "citation_year":     1920,
    "citation_archive_name": "archive.org",
    "similarity_score":  0.91,
    "chunk":             "The Five Civilized Tribes settled this land...",
}

_FAKE_EVALUATED_EVIDENCE = Evidence(
    source_id="ev-001",
    source_title="Oklahoma History Primer",
    source_url="https://archive.org/ok-primer",
    witness_citation=WitnessCitation(author="J. Smith", year=1920, archive_name="archive.org"),
    similarity_score=0.91,
    verdict=EvidenceVerdict.VERIFIED,
    chunk="The Five Civilized Tribes settled this land...",
)


class TestRunOrchestrator:
    @pytest.mark.asyncio
    async def test_truth_history_returns_lesson_response(self):
        request = _make_request(Track.TRUTH_HISTORY)

        with (
            patch("app.agents.orchestrator.hippocampus") as mock_hippo,
            patch("app.agents.orchestrator.neo4j_client") as mock_neo4j,
            patch("app.agents.orchestrator.evaluate_evidence", return_value=_FAKE_EVALUATED_EVIDENCE),
            patch("app.agents.orchestrator.search_witnesses", new_callable=AsyncMock, return_value=None),
        ):
            mock_hippo.similarity_search = AsyncMock(return_value=[_FAKE_EVIDENCE])
            mock_neo4j.run = AsyncMock(return_value=[])
            mock_neo4j.get_cross_track_context = AsyncMock(return_value=[])

            response = await run_orchestrator(request, [0.1] * 1536)

        assert response.lesson_id is not None
        assert response.track == Track.TRUTH_HISTORY
        assert response.agent_name == "HistorianAgent"
        assert len(response.blocks) == 1
        assert response.blocks[0].block_type == BlockType.PRIMARY_SOURCE
        assert len(response.xapi_statements) == 1
        assert len(response.credits_awarded) == 1

    @pytest.mark.asyncio
    async def test_homesteading_uses_lab_mission_blocks(self):
        request = _make_request(Track.HOMESTEADING)

        with (
            patch("app.agents.orchestrator.hippocampus") as mock_hippo,
            patch("app.agents.orchestrator.neo4j_client") as mock_neo4j,
            patch("app.agents.orchestrator.evaluate_evidence", return_value=_FAKE_EVALUATED_EVIDENCE),
            patch("app.agents.orchestrator.search_witnesses", new_callable=AsyncMock, return_value=None),
        ):
            mock_hippo.similarity_search = AsyncMock(return_value=[_FAKE_EVIDENCE])
            mock_neo4j.run = AsyncMock(return_value=[])
            mock_neo4j.get_cross_track_context = AsyncMock(return_value=[])

            response = await run_orchestrator(request, [0.1] * 1536)

        assert response.agent_name == "ScienceAgent"
        assert response.blocks[0].block_type == BlockType.LAB_MISSION
        assert "Homestead Lab Mission" in response.blocks[0].content

    @pytest.mark.asyncio
    async def test_discipleship_uses_narrative_blocks(self):
        request = _make_request(Track.DISCIPLESHIP)

        with (
            patch("app.agents.orchestrator.hippocampus") as mock_hippo,
            patch("app.agents.orchestrator.neo4j_client") as mock_neo4j,
            patch("app.agents.orchestrator.evaluate_evidence", return_value=_FAKE_EVALUATED_EVIDENCE),
            patch("app.agents.orchestrator.search_witnesses", new_callable=AsyncMock, return_value=None),
        ):
            mock_hippo.similarity_search = AsyncMock(return_value=[_FAKE_EVIDENCE])
            mock_neo4j.run = AsyncMock(return_value=[])
            mock_neo4j.get_cross_track_context = AsyncMock(return_value=[])

            response = await run_orchestrator(request, [0.1] * 1536)

        assert response.agent_name == "DiscipleshipAgent"
        assert response.blocks[0].block_type == BlockType.NARRATIVE

    @pytest.mark.asyncio
    async def test_empty_hippocampus_activates_researcher_then_falls_back(self):
        request = _make_request(Track.TRUTH_HISTORY)

        with (
            patch("app.agents.orchestrator.hippocampus") as mock_hippo,
            patch("app.agents.orchestrator.neo4j_client") as mock_neo4j,
            patch("app.agents.orchestrator.build_research_mission_block",
                  return_value={"content": "Go research this.", "title": "Research Mission"}),
            patch("app.agents.orchestrator.search_witnesses", new_callable=AsyncMock, return_value=None),
        ):
            mock_hippo.similarity_search = AsyncMock(return_value=[])
            mock_neo4j.run = AsyncMock(return_value=[])
            mock_neo4j.get_cross_track_context = AsyncMock(return_value=[])

            response = await run_orchestrator(request, [0.1] * 1536)

        assert response.has_research_missions is True
        assert response.blocks[0].block_type == BlockType.RESEARCH_MISSION
        assert response.researcher_activated is False
