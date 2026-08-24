import asyncio
import json

import pytest
from unittest.mock import AsyncMock, patch

from app.api.experience_builder import _emit_persisted, _run_with_progress, _stream
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
