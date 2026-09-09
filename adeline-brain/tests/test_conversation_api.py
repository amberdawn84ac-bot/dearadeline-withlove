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


def test_explicit_learning_request_teaches_instead_of_grading_the_message():
    from app.api.conversation import _build_conversation_prompt, _is_explicit_learning_request

    topic = "I want to learn about cancer. I read six kids have Ewing sarcoma in Ladera Ranch."
    assert _is_explicit_learning_request(topic)

    prompt = _build_conversation_prompt(
        topic=topic,
        tracks=["CREATION_SCIENCE"],
        grade_level="8",
        zpd_directives="",
    )

    assert "Begin teaching in this response" in prompt
    assert "Do not classify the message for school credit" in prompt
    assert "never declare causation" in prompt


def test_science_experiment_request_is_teaching_not_a_names_lecture():
    from app.api.conversation import (
        _build_conversation_prompt,
        _is_experiment_request,
        _is_explicit_learning_request,
        _wants_outside_resource,
    )

    topic = "Can we do science experiments on the homestead?"
    assert _is_experiment_request(topic)
    assert _is_explicit_learning_request(topic)
    assert _wants_outside_resource(topic)

    prompt = _build_conversation_prompt(
        topic=topic,
        tracks=["CREATION_SCIENCE"],
        grade_level="7",
        zpd_directives="",
    )
    assert "EXPERIMENT REQUEST" in prompt
    assert "Do not lecture about names" in prompt
    assert "Assign a specific" in prompt


def test_experiment_catalog_prefers_kitchen_work_for_middle_grades():
    from app.api.experiments import experiment_as_block, experiments_for_grade

    chosen = experiments_for_grade("7", limit=1)
    assert chosen
    assert chosen[0].chaos_level.value <= 2
    block = experiment_as_block(chosen[0])
    assert block["block_type"] == "EXPERIMENT"
    assert block["experiment"]["materials"]
    assert block["experiment"]["steps"]
