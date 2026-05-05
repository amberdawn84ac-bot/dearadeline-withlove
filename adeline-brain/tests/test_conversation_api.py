import json
import pytest


def _parse_sse(raw: bytes) -> list[dict]:
    events = []
    current_event: dict = {}
    for line in raw.decode().splitlines():
        if line.startswith("event: "):
            current_event["event"] = line[7:]
        elif line.startswith("data: "):
            data_str = line[6:]
            if data_str.strip():
                current_event["data"] = json.loads(data_str)
        elif line == "" and current_event:
            events.append(current_event)
            current_event = {}
    return events


def test_conversation_stream_requires_auth():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    resp = client.post("/conversation/stream", json={
        "student_id": "test-student",
        "message": "Tell me about soil",
        "track": "HOMESTEADING",
        "grade_level": "8",
        "conversation_history": [],
    })
    assert resp.status_code == 401


def test_conversation_stream_rejects_missing_message():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    resp = client.post(
        "/conversation/stream",
        json={"student_id": "s1", "grade_level": "8", "conversation_history": []},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_build_conversation_prompt_includes_mode():
    from app.api.conversation import _build_conversation_prompt
    prompt = _build_conversation_prompt(
        topic="Dust Bowl",
        tracks=["TRUTH_HISTORY"],
        grade_level="9",
        zpd_directives="ZPD: IN_ZPD",
    )
    assert "INVESTIGATOR" in prompt
    assert "Dust Bowl" in prompt
    assert "ZPD: IN_ZPD" in prompt


@pytest.mark.asyncio
async def test_build_conversation_prompt_blends_modes():
    from app.api.conversation import _build_conversation_prompt
    prompt = _build_conversation_prompt(
        topic="Soap making",
        tracks=["CREATIVE_ECONOMY", "HOMESTEADING"],
        grade_level="10",
        zpd_directives="",
    )
    assert "WORKSHOP" in prompt
    assert "LAB" in prompt
