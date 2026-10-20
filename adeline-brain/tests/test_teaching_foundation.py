"""Keep authoring within installed delivery and protect old saved work."""

import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api.classrooms import ClassroomRequest, classroom_slug, prepare_classroom
from app.curriculum.classroom import Blueprint
from app.curriculum.runtime_capabilities import authoring_capabilities
from app.schemas.api_models import Track
from tests.test_classroom import blueprint


def test_catalog_is_json_safe_and_returns_isolated_snapshots():
    first = authoring_capabilities()
    assert json.loads(json.dumps(first)) == first
    assert len(first["fingerprint"]) == 20
    first["mechanisms"].clear()
    assert len(authoring_capabilities()["mechanisms"]) == 8
    assert "generated_html_or_javascript_execution" in first["not_available"]
    assert first["delivery"]["slide"].startswith("Responsive prose")
    assert "parent" in first["evidence"]["credit"]


def test_new_canonical_identity_changes_with_delivery_contract():
    request = ClassroomRequest(topic="Matter", track=Track.CREATION_SCIENCE, level="3")
    original = classroom_slug(request)
    changed = authoring_capabilities()
    changed["fingerprint"] = "future-tested-runtime"
    with patch("app.api.classrooms.authoring_capabilities", return_value=changed):
        assert classroom_slug(request) != original
    assert classroom_slug(request) == original


@pytest.mark.asyncio
async def test_planning_receives_and_preserves_actual_delivery_capabilities():
    draft = blueprint()
    draft["teaching_design"] = {
        "approach": "guided_practice",
        "rationale": "Compare the evidence in two actual mixtures.",
        "initial_attempt": "Explain one comparison before help is offered.",
        "likely_difficulty": "May compare amounts instead of their relationship.",
        "support": "Model a different mixture with equal groups.",
        "independent_check": "Explain a fresh comparison without step hints.",
        "learning_strategy": "Predict a change and test the prediction.",
        "revisit_adds": "Connect mixture comparisons to a new representation.",
    }
    draft["scenes"][0].update(type="pbl", purpose="independent_attempt")
    draft["scenes"][3].update(purpose="independent_check")
    generated = AsyncMock(return_value=Blueprint(**draft))
    conn = AsyncMock()
    saved = []

    async def save_ready(*args, **kwargs):
        saved.append(deepcopy(kwargs["metadata"]))
        return {
            "id": "new-copy",
            "title": draft["title"],
            "metadata": kwargs["metadata"],
        }

    with (
        patch("app.services.rate_limit.enforce_rate_limit", new=AsyncMock()),
        patch(
            "app.api.classrooms.student_experience_store.get",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.api.classrooms.student_experience_store.claim",
            new=AsyncMock(return_value=SimpleNamespace(claimed=True)),
        ),
        patch("app.api.classrooms.student_experience_store.save_ready", new=save_ready),
        patch("app.api.classrooms.get_db_conn", new=AsyncMock(return_value=conn)),
        patch(
            "app.api.classrooms.canonical_store.get", new=AsyncMock(return_value=None)
        ),
        patch("app.api.classrooms.canonical_store.save", new=AsyncMock()),
        patch(
            "app.services.learning_loop.known_skills", new=AsyncMock(return_value=[])
        ),
        patch(
            "app.services.resource_router.resource_router.search",
            new=AsyncMock(return_value={"resources": []}),
        ) as searched,
        patch("app.api.classrooms.generate_json", new=generated),
    ):
        result = await prepare_classroom(
            "child",
            "new-unit",
            ClassroomRequest(topic="Mixtures", track=Track.CREATION_SCIENCE, level="3"),
        )
    assert result["phase"] == "planned"
    assert (
        generated.await_args.args[2]["runtime_capabilities"] == authoring_capabilities()
    )
    assert saved[0]["runtime_capabilities"] == authoring_capabilities()
    assert searched.await_args.args[0].grade_level == "3"
    assert generated.await_args.args[2]["learner_context"]["declared_grades"] == ["3"]
    assert saved[0]["learner_context"]["resource_grade"] == "3"
    conn.close.assert_awaited_once()
