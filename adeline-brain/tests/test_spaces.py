from unittest.mock import AsyncMock, patch

import json
import pytest

from datetime import datetime, timezone

from pydantic import ValidationError

from app.api.spaces import (
    OffPlanTopic,
    _TurnEvaluation,
    _concept_credits_for_lesson,
    _concept_slug,
    _credit_off_plan_topic,
    _decoded,
    _evaluate_turn,
    _learner_depth,
    _lesson_content,
    _lesson_for_block,
    _lesson_fully_completed,
    _newly_completed_lesson,
    _normalize_turn_payload,
    _parse_json_response,
    _proficiency_from_evaluations,
    _space_list_item,
    _space_turn_llm,
    _state,
)


def test_turn_evaluation_rejects_unsupported_resource_triggers():
    with pytest.raises(ValidationError):
        _TurnEvaluation.model_validate({
            "adeline_message": "Look closely.", "evaluation": "partial", "recommended_action": "stay",
            "is_waiting_for_user": True, "resource_triggers": ["award_credit"],
        })


def test_turn_evaluation_suggested_replies_default_to_empty():
    base = {
        "adeline_message": "Are you ready to begin?", "evaluation": "not_answered",
        "recommended_action": "stay", "is_waiting_for_user": True, "resource_triggers": [],
    }
    assert _TurnEvaluation.model_validate(base).suggested_replies == []
    assert _TurnEvaluation.model_validate({**base, "suggested_replies": ["Yes", "Not yet"]}).suggested_replies \
        == ["Yes", "Not yet"]


def test_turn_evaluation_log_fields_default_to_empty_and_can_be_tailored():
    base = {
        "adeline_message": "Record what you see today.", "evaluation": "not_answered",
        "recommended_action": "stay", "is_waiting_for_user": True, "resource_triggers": [],
    }
    assert _TurnEvaluation.model_validate(base).log_fields == []
    tailored = _TurnEvaluation.model_validate({**base, "log_fields": ["Day", "Height (cm)", "Leaf color"]})
    assert tailored.log_fields == ["Day", "Height (cm)", "Leaf color"]


def test_space_maps_blocks_to_unit_lessons():
    metadata = {"unit_plan": {"lessons": [{"lesson_id": "lesson-1", "title": "Observe", "block_ids": ["b1", "b2"]}]}}
    lesson = _lesson_for_block(metadata, "b2", 1)
    assert lesson["title"] == "Observe"
    assert lesson["index"] == 0


def test_space_state_never_indexes_past_saved_blocks():
    session = {"id": "s", "studentId": "u", "planItemId": "p", "experienceId": "e",
               "currentBlockIndex": 99, "completedBlockIds": [], "messagesJson": [],
               "status": "active", "version": 2}
    experience = {"title": "Starter", "blocks": [{"block_id": "b1"}], "metadata": {}}
    assert _state(session, experience)["current_block_index"] == 0


def test_depth_assignment_uses_saved_learner_grade_and_family_role():
    block = {"family_roles": {"middle": "Graph rise over time and interpret the rate."}}
    depth = _learner_depth({"grade_level": "Grade 7"}, block)
    assert depth == {"grade": 7, "band": "middle", "tier": "analysis",
                     "assignment": "Graph rise over time and interpret the rate."}


def test_decoded_parses_raw_jsonb_text_returned_by_asyncpg():
    # asyncpg returns jsonb columns as raw JSON text here (no codec registered) —
    # every jsonb read must go through _decoded or it silently misbehaves
    # (e.g. list("{}") == ["{", "}"], not an empty dict).
    assert _decoded('{"a": 1}', {}) == {"a": 1}
    assert _decoded(None, {"default": True}) == {"default": True}
    assert _decoded("not json", []) == []
    assert _decoded([1, 2], []) == [1, 2]  # already-decoded value passes through


LESSON = {"lesson_id": "lesson-1", "title": "Starter Culture", "concept_ids": ["c1", "c2"],
          "block_ids": ["b1", "b2"]}
UNIT_PLAN = {"essential_concepts": [
    {"concept_id": "c1", "concept": "Fermentation basics"},
    {"concept_id": "c2", "concept": "Wild yeast capture"},
]}
METADATA = {"unit_plan": {**UNIT_PLAN, "lessons": [LESSON]}}


def test_lesson_fully_completed_requires_every_block_id():
    assert not _lesson_fully_completed(LESSON, ["b1"])
    assert _lesson_fully_completed(LESSON, ["b1", "b2"])
    assert _lesson_fully_completed(LESSON, ["b1", "b2", "b3"])


def test_lesson_fully_completed_is_false_for_a_lesson_with_no_blocks():
    assert not _lesson_fully_completed({"block_ids": []}, ["b1"])


def test_newly_completed_lesson_fires_only_on_the_completing_block():
    # Completing b1 alone doesn't finish the lesson yet.
    assert _newly_completed_lesson(METADATA, "b1", [], ["b1"], []) is None
    # Completing b2 (the last block) finishes it.
    result = _newly_completed_lesson(METADATA, "b2", ["b1"], ["b1", "b2"], [])
    assert result is not None
    assert result["lesson_id"] == "lesson-1"


def test_newly_completed_lesson_does_not_refire_if_already_fully_completed_before():
    # Both snapshots already show the lesson fully completed — not "newly" completed.
    assert _newly_completed_lesson(METADATA, "b2", ["b1", "b2"], ["b1", "b2"], []) is None


def test_newly_completed_lesson_never_refires_for_an_already_credited_lesson():
    # Idempotency: a replayed/retried transition must not re-trigger credit.
    result = _newly_completed_lesson(METADATA, "b2", ["b1"], ["b1", "b2"], ["lesson-1"])
    assert result is None


def test_newly_completed_lesson_returns_none_for_an_unmapped_block():
    assert _newly_completed_lesson(METADATA, "unknown-block", [], ["unknown-block"], []) is None


def test_proficiency_from_evaluations_ladder():
    assert _proficiency_from_evaluations([]) == "DEVELOPING"
    assert _proficiency_from_evaluations(["incorrect", "incorrect"]) == "DEVELOPING"
    assert _proficiency_from_evaluations(["correct", "partial"]) == "UNDERSTANDING"
    assert _proficiency_from_evaluations(["correct", "correct"]) == "EXTENDING"


def test_concept_credits_for_lesson_resolves_ids_against_essential_concepts():
    credits = _concept_credits_for_lesson(UNIT_PLAN, LESSON)
    assert [c.concept_id for c in credits] == ["c1", "c2"]
    assert [c.concept_name for c in credits] == ["Fermentation basics", "Wild yeast capture"]


def test_concept_credits_for_lesson_skips_unknown_concept_ids():
    lesson = {"concept_ids": ["c1", "unknown"], "block_ids": ["b1"]}
    credits = _concept_credits_for_lesson(UNIT_PLAN, lesson)
    assert [c.concept_id for c in credits] == ["c1"]


def test_lesson_content_joins_only_blocks_belonging_to_the_lesson():
    blocks = [
        {"block_id": "b1", "title": "Day 1", "content": "Feed the starter."},
        {"block_id": "b2", "title": "Day 2", "content": "Check for bubbles."},
        {"block_id": "b3", "title": "Unrelated", "content": "Different lesson entirely."},
    ]
    content = _lesson_content(blocks, LESSON)
    assert "Feed the starter" in content
    assert "Check for bubbles" in content
    assert "Unrelated" not in content


def test_concept_slug_normalizes_arbitrary_concept_names():
    assert _concept_slug("Why does yeast make bubbles?!") == "why-does-yeast-make-bubbles"
    assert _concept_slug("  Osmosis  ") == "osmosis"
    assert _concept_slug("???") == "topic"


@pytest.mark.asyncio
async def test_demonstrated_off_plan_topic_gets_full_mastery_credit():
    topic = OffPlanTopic(concept_name="Osmosis", track=None, tier="demonstrated")
    with (
        patch("app.api.spaces._topic_oas_standards", new=AsyncMock(return_value=[{"standard_id": "SCI.1"}])),
        patch("app.api.spaces.record_mastery_credit", new=AsyncMock()) as mock_credit,
    ):
        result = await _credit_off_plan_topic(
            student_id="student-1", plan_item_id="plan-1", session_id="session-1",
            fallback_track="CREATION_SCIENCE", fallback_grade=7, topic=topic,
        )

    assert result == "Osmosis"
    mock_credit.assert_awaited_once()
    kwargs = mock_credit.call_args.kwargs
    assert kwargs["track"] == "CREATION_SCIENCE"
    assert kwargs["oas_standards"] == [{"standard_id": "SCI.1"}]
    assert kwargs["concept_credits"][0].concept_name == "Osmosis"
    assert kwargs["lesson_id"] == "rabbit-hole-osmosis-student-1"


@pytest.mark.asyncio
async def test_encountered_off_plan_topic_is_logged_not_credited():
    topic = OffPlanTopic(concept_name="Capillary action", track=None, tier="encountered")
    with (
        patch("app.api.spaces.record_mastery_credit", new=AsyncMock()) as mock_credit,
        patch("app.api.spaces.concept_encounter_store.record", new=AsyncMock()) as mock_record,
    ):
        result = await _credit_off_plan_topic(
            student_id="student-1", plan_item_id="plan-1", session_id="session-1",
            fallback_track="CREATION_SCIENCE", fallback_grade=7, topic=topic,
        )

    assert result is None
    mock_credit.assert_not_awaited()
    mock_record.assert_awaited_once_with("student-1", "Capillary action", "CREATION_SCIENCE", "session-1")


@pytest.mark.asyncio
async def test_off_plan_topic_track_override_takes_precedence_over_fallback():
    topic = OffPlanTopic(concept_name="Regulatory capture", track="JUSTICE_CHANGEMAKING", tier="encountered")
    with patch("app.api.spaces.concept_encounter_store.record", new=AsyncMock()) as mock_record:
        await _credit_off_plan_topic(
            student_id="student-1", plan_item_id="plan-1", session_id="session-1",
            fallback_track="TRUTH_HISTORY", fallback_grade=9, topic=topic,
        )
    mock_record.assert_awaited_once_with("student-1", "Regulatory capture", "JUSTICE_CHANGEMAKING", "session-1")


@pytest.mark.asyncio
async def test_off_plan_topic_failure_is_swallowed_not_raised():
    topic = OffPlanTopic(concept_name="Osmosis", track=None, tier="demonstrated")
    with patch("app.api.spaces._topic_oas_standards", new=AsyncMock(side_effect=RuntimeError("pgvector down"))):
        result = await _credit_off_plan_topic(
            student_id="student-1", plan_item_id="plan-1", session_id="session-1",
            fallback_track="CREATION_SCIENCE", fallback_grade=7, topic=topic,
        )
    assert result is None


def test_space_list_item_shapes_a_db_row_into_the_list_response():
    row = {
        "planItemId": "family-abc-science-0", "status": "active",
        "completedBlockIds": ["b1", "b2"], "updatedAt": datetime(2026, 9, 5, tzinfo=timezone.utc),
        "title": "Kitchen Chemistry: Sourdough", "track": "CREATION_SCIENCE", "total_blocks": 8,
    }
    item = _space_list_item(row)
    assert item["plan_item_id"] == "family-abc-science-0"
    assert item["completed_blocks"] == 2
    assert item["total_blocks"] == 8
    assert item["updated_at"] == "2026-09-05T00:00:00+00:00"


def test_space_list_item_handles_missing_completed_blocks_and_updated_at():
    row = {
        "planItemId": "family-abc-history-0", "status": "completed",
        "completedBlockIds": None, "updatedAt": None,
        "title": "The Poison Squad", "track": "TRUTH_HISTORY", "total_blocks": None,
    }
    item = _space_list_item(row)
    assert item["completed_blocks"] == 0
    assert item["total_blocks"] == 0
    assert item["updated_at"] is None


_TURN_JSON = {
    "adeline_message": "What did the starter smell like this morning?",
    "evaluation": "not_answered",
    "recommended_action": "stay",
    "is_waiting_for_user": True,
}


def _space_state() -> dict:
    return {
        "status": "active",
        "title": "Kitchen Chemistry: Sourdough",
        "current_lesson": {"title": "Starter Culture"},
        "current_block_index": 0,
        "total_blocks": 3,
        "current_block": {"block_id": "b1", "content": "Feed the starter and record what you see."},
        "messages": [],
    }


def test_parse_json_response_extracts_object_from_prose_and_fences():
    assert _parse_json_response('Here you go:\n{"adeline_message": "Hi", "evaluation": "partial"}')["evaluation"] == "partial"
    fenced = '```json\n{"adeline_message": "Hi", "evaluation": "correct"}\n```'
    assert _parse_json_response(fenced)["evaluation"] == "correct"


def test_parse_json_response_decodes_langchain_content_blocks():
    content = [{"type": "text", "text": '```json\n{"adeline_message": "Look closer.", "evaluation": "partial"}\n```'}]
    assert _parse_json_response(content)["adeline_message"] == "Look closer."


def test_parse_json_response_rejects_empty_fence_with_a_clear_error():
    with pytest.raises(ValueError, match="Empty JSON after fence-stripping"):
        _parse_json_response("```")


def test_normalize_turn_payload_coerces_case_and_drops_unknown_triggers():
    payload = _normalize_turn_payload({
        "adeline_message": "Tell me more.",
        "evaluation": "Partial",
        "recommended_action": "STAY",
        "is_waiting_for_user": "true",
        "resource_triggers": ["show_microscope_diagram", "award_credit"],
    })
    assert payload["evaluation"] == "partial"
    assert payload["recommended_action"] == "stay"
    assert payload["is_waiting_for_user"] is True
    assert payload["resource_triggers"] == ["show_microscope_diagram"]


def test_normalize_turn_payload_turns_null_lists_and_empty_off_plan_into_defaults():
    payload = _normalize_turn_payload({
        "adeline_message": "Keep going.",
        "evaluation": "correct",
        "recommended_action": "stay",
        "is_waiting_for_user": True,
        "resource_triggers": None,
        "suggested_replies": None,
        "log_fields": None,
        "off_plan_topic": {},
    })
    assert payload["resource_triggers"] == []
    assert payload["suggested_replies"] == []
    assert payload["log_fields"] == []
    assert payload["off_plan_topic"] is None
    _TurnEvaluation.model_validate(payload)


def test_space_turn_llm_uses_the_known_good_constructor(monkeypatch):
    captured = {}

    def fake_create_llm(model=None, **kwargs):
        captured["model"] = model
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setenv("ADELINE_SPACE_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr("app.api.spaces.create_llm", fake_create_llm)
    _space_turn_llm()
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["kwargs"] == {"max_tokens": 4096}


@pytest.mark.asyncio
async def test_evaluate_turn_falls_back_if_llm_constructor_fails(monkeypatch):
    def boom():
        raise TypeError("unexpected keyword argument 'thinking_budget'")

    monkeypatch.setattr("app.api.spaces._space_turn_llm", boom)
    monkeypatch.setattr("app.api.spaces.asyncio.sleep", AsyncMock())

    result = await _evaluate_turn(_space_state(), "We mixed flour and water.")

    assert result.evaluation == "not_answered"
    assert result.recommended_action == "stay"
    assert "say that again" in result.adeline_message.lower()


class _FakeResponse:
    def __init__(self, content, metadata=None):
        self.content = content
        self.response_metadata = metadata or {}


class _FakeLLM:
    def __init__(self, responses=None, errors=None):
        self._responses = list(responses or [])
        self._errors = list(errors or [])
        self.calls = 0

    async def ainvoke(self, _messages):
        self.calls += 1
        if self._errors:
            raise self._errors.pop(0)
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_evaluate_turn_recovers_from_empty_fence_then_parses_content_blocks(monkeypatch):
    llm = _FakeLLM(responses=[
        _FakeResponse("```"),
        _FakeResponse([{"type": "text", "text": json.dumps(_TURN_JSON)}]),
    ])
    monkeypatch.setattr("app.api.spaces._space_turn_llm", lambda: llm)
    monkeypatch.setattr("app.api.spaces.asyncio.sleep", AsyncMock())

    result = await _evaluate_turn(_space_state(), "It smelled tangy and had bubbles.")

    assert llm.calls == 2
    assert result.adeline_message == _TURN_JSON["adeline_message"]
    assert result.evaluation == "not_answered"
    assert result.recommended_action == "stay"


@pytest.mark.asyncio
async def test_evaluate_turn_falls_back_instead_of_failing_the_family(monkeypatch):
    llm = _FakeLLM(responses=[_FakeResponse(""), _FakeResponse("```"), _FakeResponse("not json")])
    monkeypatch.setattr("app.api.spaces._space_turn_llm", lambda: llm)
    monkeypatch.setattr("app.api.spaces.asyncio.sleep", AsyncMock())

    result = await _evaluate_turn(_space_state(), "We mixed flour and water.")

    assert llm.calls == 3
    assert result.evaluation == "not_answered"
    assert result.recommended_action == "stay"
    assert "say that again" in result.adeline_message.lower()


@pytest.mark.asyncio
async def test_evaluate_turn_retries_rate_limit_then_succeeds(monkeypatch):
    llm = _FakeLLM(
        errors=[RuntimeError("429 Resource exhausted")],
        responses=[_FakeResponse(json.dumps(_TURN_JSON))],
    )
    monkeypatch.setattr("app.api.spaces._space_turn_llm", lambda: llm)
    monkeypatch.setattr("app.api.spaces.asyncio.sleep", AsyncMock())

    result = await _evaluate_turn(_space_state(), "Ready.")

    assert llm.calls == 2
    assert result.adeline_message == _TURN_JSON["adeline_message"]
