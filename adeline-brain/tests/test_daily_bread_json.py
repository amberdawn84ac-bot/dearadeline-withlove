import json
from unittest.mock import AsyncMock

import pytest
from fastapi import Response

from app.api.daily_bread import _FALLBACKS, _complete_lesson, _json_object, daily_bread


def test_daily_bread_decodes_langchain_content_blocks():
    content = [{
        "type": "text",
        "text": "```json\n{\"reference\":\"Mishlei 3:5\",\"verse\":\"Trust in YHWH.\"}\n```",
    }]

    assert _json_object(content) == {
        "reference": "Mishlei 3:5",
        "verse": "Trust in YHWH.",
    }


def test_daily_bread_extracts_object_without_accepting_explanation_as_json():
    content = "Here is the object:\n{\"rendering\": \"Hear, Yisrael.\"}\nDone."

    assert _json_object(content)["rendering"] == "Hear, Yisrael."


def test_daily_bread_rejects_missing_json_object():
    with pytest.raises(ValueError, match="did not contain"):
        _json_object([{"type": "text", "text": "No structured response"}])


@pytest.mark.asyncio
async def test_daily_bread_reads_today_cache_before_history(monkeypatch):
    from app.connections import redis_client as redis_module

    cached = _complete_lesson(dict(_FALLBACKS[0]))
    redis = AsyncMock()
    redis.get.return_value = json.dumps(cached)
    monkeypatch.setattr(redis_module, "redis_client", redis)

    result = await daily_bread(Response())

    assert result.reference == cached["reference"]
    redis.get.assert_awaited_once()
