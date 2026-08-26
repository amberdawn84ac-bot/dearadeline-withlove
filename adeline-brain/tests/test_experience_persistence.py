import asyncio
import json

import pytest
from unittest.mock import AsyncMock, patch

from app.api.experience_builder import _emit_persisted, _run_with_progress, _stream, sequence_bridge_block
from app.agents.adapter import AdaptationRequest
from app.connections.student_experience_store import GenerationClaim
from app.schemas.api_models import LessonRequest, Track


def _request() -> LessonRequest:
    return LessonRequest(
        student_id="student-1",
        plan_item_id="today-item-1",
        topic="Kitchen Chemistry",
        track=Track.CREATION_SCIENCE,
        grade_level="8",
        required_standard_codes=["OAS.SCI.8.1"],
    )


def test_supported_mission_gets_a_real_readiness_bridge():
    request = _request().model_copy(update={
        "sequence_policy": "SUPPORTED",
        "sequence_state": "BRIDGE_REQUIRED",
        "bridge_required": True,
    })
    bridge = sequence_bridge_block(request)
    assert bridge is not None
    assert bridge["metadata"]["sequence_bridge"] is True
    assert bridge["metadata"]["not_mastery_evidence"] is True
    assert "not a separate worksheet" in bridge["content"]


def test_ready_hard_concept_does_not_get_redundant_bridge():
    request = _request().model_copy(update={
        "concept_id": "cs-001",
        "sequence_policy": "HARD",
        "sequence_state": "READY",
        "bridge_required": False,
    })
    assert sequence_bridge_block(request) is None


async def _events(record: dict) -> list[dict]:
    result = []
    async for frame in _emit_persisted(_request(), record):
        result.append(json.loads(frame.removeprefix("data: ").strip()))
    return result


@pytest.mark.asyncio
async def test_persisted_experience_reuses_exact_lesson_and_blocks():
    record = {
        "id": "experience-stable-id",
        "status": "ready",
        "title": "Kitchen Chemistry",
        "track": "CREATION_SCIENCE",
        "blocks": [{"block_id": "experience-stable-id-0", "block_type": "NARRATIVE", "content": "Exact saved text"}],
        "metadata": {"required_standard_codes": ["OAS.SCI.8.1"]},
    }

    first = await _events(record)
    second = await _events(record)

    assert first == second
    assert first[0]["block"]["content"] == "Exact saved text"
    assert first[-1]["lesson_id"] == "experience-stable-id"
    assert first[-1]["credits_awarded"] == []


@pytest.mark.asyncio
async def test_persisted_experience_keeps_original_standard_targets():
    record = {
        "id": "experience-2",
        "status": "ready",
        "title": "Saved lesson",
        "track": "CREATION_SCIENCE",
        "blocks": [],
        "metadata": {"required_standard_codes": ["ORIGINAL.STANDARD"]},
    }
    events = await _events(record)
    assert events[-1]["oas_standards"][0]["standard_id"] == "ORIGINAL.STANDARD"


@pytest.mark.asyncio
async def test_reopening_ready_experience_makes_zero_author_or_resource_calls():
    record = {
        "id": "experience-ready",
        "status": "ready",
        "title": "Saved lesson",
        "track": "CREATION_SCIENCE",
        "blocks": [{"block_id": "experience-ready-0", "block_type": "EXPERIMENT", "content": "Saved"}],
        "metadata": {"required_standard_codes": ["ORIGINAL.STANDARD"]},
    }
    author = AsyncMock()
    resource_search = AsyncMock()
    with (
        patch("app.api.experience_builder.student_experience_store.claim", new=AsyncMock(
            return_value=GenerationClaim("ready", False, record)
        )),
        patch("app.api.experience_builder._author", new=author),
        patch("app.api.experience_builder.resource_router.search", new=resource_search),
    ):
        first = [frame async for frame in _stream(_request())]
        second = [frame async for frame in _stream(_request())]

    assert first == second
    author.assert_not_awaited()
    resource_search.assert_not_awaited()


@pytest.mark.asyncio
async def test_preseeded_canonical_opens_without_author_or_resource_search():
    canonical = {
        "id": "canonical-1",
        "title": "Kitchen Chemistry",
        "blocks": [{
            "block_id": "canonical-block-1",
            "block_type": "EXPERIMENT",
            "experience_stage": "ACTION",
            "content": "Compare how two dough samples rise.",
            "family_style": True,
            "canonical_format_version": 10,
            "family_roles": {
                "elementary": "Notice and draw.",
                "middle": "Measure and compare.",
                "high_school": "Control variables and explain.",
            },
            "metadata": {"canonical_contract": {"family_roles": {}}},
        }],
    }
    saved = {
        "id": "experience-new",
        "status": "ready",
        "title": "Kitchen Chemistry",
        "track": "CREATION_SCIENCE",
        "blocks": canonical["blocks"],
        "metadata": {"required_standard_codes": ["OAS.SCI.8.1"]},
    }
    author = AsyncMock()
    resource_search = AsyncMock()
    with (
        patch("app.api.experience_builder.student_experience_store.claim", new=AsyncMock(
            return_value=GenerationClaim("generating", True, {"id": "experience-new"})
        )),
        patch("app.api.experience_builder.canonical_store.get", new=AsyncMock(return_value=canonical)),
        patch("app.api.experience_builder.is_current_family_canonical", return_value=True),
        patch("app.api.experience_builder.adaptation_for", new=AsyncMock(return_value=AdaptationRequest(
            grade_level="8", track="CREATION_SCIENCE"
        ))),
        patch("app.api.experience_builder.student_experience_store.save_ready", new=AsyncMock(return_value=saved)),
        patch("app.api.experience_builder._author", new=author),
        patch("app.api.experience_builder.resource_router.search", new=resource_search),
    ):
        events = [frame async for frame in _stream(_request())]

    author.assert_not_awaited()
    resource_search.assert_not_awaited()
    assert any('"type": "done"' in frame for frame in events)


@pytest.mark.asyncio
async def test_long_generation_emits_progress_before_exact_result():
    async def slow_result():
        await asyncio.sleep(0.025)
        return {"blocks": ["exact"]}

    events = [
        event async for event in _run_with_progress(
            slow_result(),
            ("Working carefully…", "Still checking…"),
            interval_seconds=0.005,
        )
    ]

    assert events[0] == ("status", "Working carefully…")
    assert any(event == ("status", "Still checking…") for event in events)
    assert events[-1] == ("result", {"blocks": ["exact"]})


@pytest.mark.asyncio
async def test_fast_generation_returns_without_fake_progress():
    async def immediate_result():
        return "ready"

    events = [
        event async for event in _run_with_progress(
            immediate_result(), ("Should not appear",), interval_seconds=0.1,
        )
    ]

    assert events == [("result", "ready")]
