"""Production failure regressions, with no paid provider calls."""

import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest

from app.api import classrooms as api
from app.curriculum.classroom import (
    Blueprint, CLASSROOM_AUTHORING_REVISION, RUBRIC_CONTRACT_REVISION,
)
from app.curriculum.estuary_classroom import estuary_classroom
from app.curriculum.runtime_capabilities import authoring_capabilities
from tests.test_autonomous_rubrics import rubric


def context():
    return {
        "track": "CREATION_SCIENCE",
        "authoring_revision": CLASSROOM_AUTHORING_REVISION,
        "rubric_contract": RUBRIC_CONTRACT_REVISION,
        "runtime_capabilities": authoring_capabilities(),
    }


def valid_plan():
    plan = estuary_classroom().blueprint.model_dump(mode="json")
    plan["class_quality_rubric"] = rubric()
    plan["mastery_rubric"] = rubric()
    return plan


def response(plan):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(plan)), finish_reason="stop",
    )])


def test_new_authoring_requires_evidence_and_rubrics_without_breaking_saved_reading():
    contract = api.authoring_contract(Blueprint, context())
    evidence = contract["$defs"]["SceneBrief"]["properties"]["evidence"]
    assert evidence["type"] == "string" and evidence["minLength"] == 1
    assert "evidence" in contract["$defs"]["SceneBrief"]["required"]
    for name in ("teaching_design", "mastery_rubric", "class_quality_rubric"):
        assert "$ref" in contract["properties"][name]
        assert name in contract["required"]
    old = valid_plan()
    old["scenes"][0]["evidence"] = None
    old["mastery_rubric"] = old["class_quality_rubric"] = None
    assert Blueprint.model_validate(old).scenes[0].evidence is None
    # JSON-only fallback providers receive the same contract in the prompt.
    assert api.authoring_response_format("groq", Blueprint, context()) == {"type": "json_object"}


def test_all_missing_scene_evidence_is_reported_in_one_repair():
    plan = valid_plan()
    for scene in plan["scenes"]:
        scene["evidence"] = None
    with pytest.raises(ValueError) as exc:
        api.validate_draft(Blueprint, json.dumps(plan), context())
    assert all(f"{scene['id']}.evidence" in str(exc.value) for scene in plan["scenes"])


@pytest.mark.asyncio
async def test_schema_negotiation_keeps_request_cap_and_json_mode_uses_full_contract(monkeypatch):
    for key, value in {
        "GEMINI_API_KEY": "test", "GOOGLE_API_KEY": "", "OPENAI_API_KEY": "",
        "GROQ_API_KEY": "", "_provider_retry_at": 0, "_fallback_retry_at": 0,
        "_groq_retry_at": 0,
    }.items():
        monkeypatch.setattr(api, key, value)
    plan = valid_plan()
    missing = deepcopy(plan)
    missing["scenes"][0]["evidence"] = None
    missing["scenes"][1]["evidence"] = None
    choices = [
        openai.BadRequestError(
            "response_format schema unsupported",
            response=httpx.Response(400, request=httpx.Request("POST", "https://provider.test")),
            body={"error": {"message": "schema unsupported"}},
        ),
        response(missing), response(plan),
    ]
    calls = []

    async def create(**kwargs):
        calls.append(deepcopy(kwargs))
        result = choices.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=create)
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=client)
    manager.__aexit__ = AsyncMock(return_value=False)
    with patch("openai.AsyncOpenAI", return_value=manager):
        result = await api.generate_json("Teach the topic.", Blueprint, context())
    assert result.title == plan["title"]
    assert len(calls) == 3  # request ceiling is unchanged, including negotiation
    assert all(call["response_format"] == {"type": "json_object"} for call in calls[1:])
    prompt_contract = json.loads(calls[1]["messages"][0]["content"].split("JSON schema:\n")[1].split("\nGenerate")[0])
    assert prompt_contract == api.authoring_contract(Blueprint, context())
    repair = calls[2]["messages"][-1]["content"]
    assert all(f"{scene['id']}.evidence" in repair for scene in missing["scenes"][:2])
    assert "not a summary slide" in repair


def test_workshop_summary_slide_is_still_rejected():
    plan = valid_plan()
    plan["scenes"][-1]["type"] = "slide"
    plan["scenes"][-1]["purpose"] = "reflect"
    with pytest.raises(ValueError, match="ends with work"):
        api.validate_draft(Blueprint, json.dumps(plan), context())
