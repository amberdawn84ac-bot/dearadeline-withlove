import json

import pytest

from app.api.experience_builder import _emit_persisted
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
    assert first[-1]["credits_awarded"][0]["lesson_id"] == "experience-stable-id"


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
