from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest
from app.agents.persona import ADELINE_CLASSROOM_PERSONA
from app.api.classrooms import (
    ClassroomRequest,
    build_document,
    classroom_slug,
    public_state,
)
from app.curriculum.classroom import (
    CLASSROOM_VERSION,
    Blueprint,
    Classroom,
    Scene,
    public_classroom,
)
from app.schemas.api_models import Track
from pydantic import ValidationError


def blueprint():
    return {
        "title": "Mixtures",
        "understanding": "Ratios compare quantities multiplicatively.",
        "essential_question": "How can we compare mixtures?",
        "demonstration": "Compare and explain two new mixtures.",
        "integrated_tracks": ["CREATION_SCIENCE", "APPLIED_MATHEMATICS"],
        "roster": [
            {
                "id": "adeline",
                "name": "Adeline",
                "role": "teacher",
                "persona": "Warm, knowledgeable mentor.",
            },
            {
                "id": "peer",
                "name": "Colleague",
                "role": "assistant",
                "persona": "Asks for evidence and clarification.",
            },
        ],
        "scenes": [
            {
                "id": f"s{i}",
                "title": f"Compare mixture {i}",
                "type": "quiz" if i == 3 else "slide",
                "objective": "Explain the quantities.",
                "brief": "Show a concrete example and explain it.",
            }
            for i in range(4)
        ],
        "next_revisit": "Connect ratios to graphs in another context.",
    }


def scene(i):
    return {
        "id": f"s{i}",
        "title": "Compare mixtures",
        "type": "quiz" if i == 3 else "slide",
        "content": "One cup to two cups gives a 1:2 ratio.",
        "actions": [
            {"role_id": "adeline", "text": "What changes when both amounts double?"}
        ],
        "learner_task": "Explain the comparison.",
        "success_criteria": ["Use multiplicative reasoning."],
        "family_roles": {
            "elementary": "Draw amounts.",
            "middle": "Compare ratios.",
            "high_school": "Justify scaling.",
        },
        **(
            {
                "question": {
                    "prompt": "Which equals 1:2?",
                    "choices": [
                        {"id": "a", "label": "2:4"},
                        {"id": "b", "label": "2:3"},
                    ],
                    "answer": "a",
                    "explanation": "Multiplying both amounts by two preserves the ratio.",
                }
            }
            if i == 3
            else {}
        ),
    }


def test_complete_classroom_hides_keys_and_teacher_briefs():
    actual = Classroom(
        blueprint=Blueprint(**blueprint()), scenes=[Scene(**scene(i)) for i in range(4)]
    )
    public = public_classroom(actual)
    assert "answer" not in public["scenes"][3]["question"]
    assert "explanation" not in public["scenes"][3]["question"]
    assert "scenes" not in public["blueprint"]
    assert actual.scenes[3].question.answer == "a"


def test_incomplete_documents_and_fake_activities_are_rejected():
    data = blueprint()
    data["roster"][0]["name"] = "Other teacher"
    with pytest.raises(ValidationError):
        Blueprint(**data)
    with pytest.raises(ValidationError):
        Classroom(blueprint=Blueprint(**blueprint()), scenes=[Scene(**scene(0))])
    data = scene(3)
    data["question"]["answer"] = "missing"
    with pytest.raises(ValidationError):
        Scene(**data)
    data = scene(0)
    data["type"] = "interactive"
    with pytest.raises(ValidationError):
        Scene(**data)


def test_simulation_domains():
    from app.curriculum.classroom import Simulation

    var = {"label": "Amount", "minimum": 0, "maximum": 10, "initial": 5, "step": 1}
    data = {
        "model": "mixture_fraction",
        "x": var,
        "y": var,
        "output_label": "Fraction",
        "explanation": "First amount divided by the total amount.",
        "prediction_prompt": "Predict the change.",
        "observation_prompt": "Explain the change.",
    }
    with pytest.raises(ValidationError):
        Simulation(**data)
    data["x"] = {**var, "minimum": 1}
    assert Simulation(**data)
    data["x"]["initial"] = 20
    with pytest.raises(ValidationError):
        Simulation(**data)


def test_identity_tracks_and_legacy_boundary():
    assert len(Track) == 10
    assert "Warm, sharp-witted" in ADELINE_CLASSROOM_PERSONA
    assert "SCRIPTURE" in ADELINE_CLASSROOM_PERSONA
    from app.api.classrooms import document_from
    from app.curriculum.builtin_canonicals import builtin_canonical
    from app.jobs.canonical_seeding import canonical_seeding_enabled

    assert builtin_canonical("old") is None
    assert not canonical_seeding_enabled()
    assert document_from({"metadata": {"unit_plan": {}}}) is None
    req = ClassroomRequest(topic="Mixtures", track=Track.CREATION_SCIENCE)
    assert classroom_slug(req) != classroom_slug(
        req.model_copy(update={"topic": "Other"})
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_build_checkpoints_and_honest_completion(fail):
    record = {
        "id": "copy",
        "track": "CREATION_SCIENCE",
        "metadata": {
            "format_version": CLASSROOM_VERSION,
            "phase": "planned",
            "blueprint": blueprint(),
            "scenes": [],
            "request": {"topic": "Mixtures"},
            "canonical_slug": "new-slug",
            "responses": {},
        },
    }
    conn = AsyncMock()
    conn.fetchval.return_value = True
    saved = []

    async def save(*args):
        saved.append(deepcopy(args[-1]))
        return record

    generated = AsyncMock(
        side_effect=ValueError("invalid scene")
        if fail
        else [Scene(**scene(i)) for i in range(4)]
    )
    with (
        patch("app.api.classrooms.get_db_conn", new=AsyncMock(return_value=conn)),
        patch(
            "app.api.classrooms.student_experience_store.get",
            new=AsyncMock(return_value=record),
        ),
        patch("app.api.classrooms.generate_json", new=generated),
        patch("app.api.classrooms.save_document", new=save),
        patch(
            "app.api.classrooms.canonical_store.get", new=AsyncMock(return_value=None)
        ),
        patch("app.api.classrooms.canonical_store.save", new=AsyncMock()) as canonical,
    ):
        await build_document("student", "unit")
    if fail:
        assert saved[-1]["phase"] == "failed"
        assert saved[-1]["scenes"] == []
        canonical.assert_not_awaited()
    else:
        from app.curriculum.runtime_capabilities import authoring_capabilities

        assert all(
            call.args[2]["runtime_capabilities"] == authoring_capabilities()
            for call in generated.await_args_list
        )
        assert [len(d["scenes"]) for d in saved] == [0, 1, 2, 3, 4, 4]
        assert saved[-1]["phase"] == "ready"
        assert canonical.await_args.args[1]["contract_version"] == 100
        assert (
            public_state({"id": "x", "title": "Mixtures", "metadata": saved[-1]})[
                "phase"
            ]
            == "ready"
        )
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_generation_injects_adeline_persona_and_exact_ten_tracks():
    import json
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from app.api.classrooms import generate_json

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(blueprint())),
                    finish_reason="stop",
                )
            ]
        )
    )
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=client)
    manager.__aexit__ = AsyncMock(return_value=False)
    with (
        patch("app.api.classrooms.GEMINI_API_KEY", "test-only"),
        patch("openai.AsyncOpenAI", return_value=manager),
    ):
        result = await generate_json(
            "Plan a classroom.", Blueprint, {"topic": "Mixtures"}
        )
    prompt = client.chat.completions.create.await_args.kwargs["messages"][0]["content"]
    assert "Warm, sharp-witted" in prompt
    assert "YHWH" in prompt
    for track in Track:
        assert track.value in prompt
    assert result.roster[0].name == "Adeline"


def sorting_scene():
    data = scene(0)
    data.update(
        type="interactive",
        sorting={
            "instruction": "Sort each sample by its observed state.",
            "categories": [
                {"id": "solid", "label": "Solid"},
                {"id": "liquid", "label": "Liquid"},
            ],
            "items": [
                {
                    "id": "rock",
                    "label": "Rock at room temperature",
                    "category_id": "solid",
                    "explanation": "The rock retains its shape.",
                },
                {
                    "id": "water",
                    "label": "Water at room temperature",
                    "category_id": "liquid",
                    "explanation": "Water flows and takes its container's shape.",
                },
            ],
        },
    )
    return data


def test_level_changes_reuse_identity():
    req = ClassroomRequest(
        topic="Matter", track=Track.CREATION_SCIENCE, level="3rd grade"
    )
    assert classroom_slug(req) != classroom_slug(
        req.model_copy(update={"level": "8th grade"})
    )
    assert classroom_slug(req) == classroom_slug(
        req.model_copy(update={"level": " 3RD GRADE "})
    )


def test_sorting_hides_keys_and_requires_one_real_mechanism():
    scenes = [Scene(**sorting_scene()), *[Scene(**scene(i)) for i in range(1, 4)]]
    bp = blueprint()
    bp["scenes"][0]["type"] = "interactive"
    result = public_classroom(Classroom(blueprint=Blueprint(**bp), scenes=scenes))
    assert result["scenes"][0]["sorting"]["items"][0] == {
        "id": "rock",
        "label": "Rock at room temperature",
    }
    bad = sorting_scene()
    bad["sorting"]["items"][0]["category_id"] = "gas"
    with pytest.raises(ValidationError):
        Scene(**bad)
    bad = sorting_scene()
    bad["sorting"]["items"][1]["id"] = "rock"
    with pytest.raises(ValidationError):
        Scene(**bad)


def test_sorting_feedback_is_server_checked_and_rejects_partial_or_invalid_work():
    from app.curriculum.classroom_evidence import check_sorting

    spec = Scene(**sorting_scene()).sorting
    assert check_sorting(spec, '{"rock":"solid","water":"liquid"}')["correct"]
    feedback = check_sorting(spec, '{"rock":"liquid","water":"liquid"}')
    assert not feedback["correct"]
    assert feedback["items"][0]["explanation"] == "The rock retains its shape."
    for text in [
        "{}",
        "[]",
        "invalid",
        '{"rock":"solid"}',
        '{"rock":[],"water":"liquid"}',
        '{"rock":"gas","water":"liquid"}',
    ]:
        with pytest.raises(ValueError):
            check_sorting(spec, text)


def test_teaching_contract_requires_independent_checks_and_workshop_application():
    data = blueprint()
    data["teaching_design"] = {
        "approach": "workshop",
        "rationale": "Test and compare mixtures directly.",
        "initial_attempt": "Explain an unfamiliar mixture before help.",
        "likely_difficulty": "May confuse absolute amounts with ratios.",
        "support": "Compare a different example with equal groups.",
        "independent_check": "Compare fresh ratios without step hints.",
        "learning_strategy": "Predict the result before changing amounts.",
        "revisit_adds": "Connect mixture ratios to coordinate graphs.",
    }
    with pytest.raises(ValidationError):
        Blueprint(**data)
    data["scenes"][0].update(type="pbl", purpose="independent_attempt")
    data["scenes"][3].update(purpose="independent_check")
    assert Blueprint(**data).teaching_design.approach == "workshop"
    data["scenes"][3].update(type="slide")
    with pytest.raises(ValidationError):
        Blueprint(**data)


@pytest.mark.asyncio
async def test_existing_classroom_reopens_after_level_identity_fix():
    from app.api.classrooms import prepare_classroom

    req = ClassroomRequest(topic="Mixtures", track=Track.CREATION_SCIENCE)
    record = {
        "id": "old",
        "title": "Mixtures",
        "metadata": {
            "format_version": CLASSROOM_VERSION,
            "phase": "planned",
            "blueprint": blueprint(),
            "canonical_slug": "pre-level-identity-slug",
            "request": req.model_dump(mode="json"),
        },
    }
    with (
        patch("app.services.rate_limit.enforce_rate_limit", new=AsyncMock()),
        patch(
            "app.api.classrooms.student_experience_store.get",
            new=AsyncMock(return_value=record),
        ),
    ):
        result = await prepare_classroom("child", "unit", req)
        assert result["id"] == "old"
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await prepare_classroom(
                "child", "unit", req.model_copy(update={"level": "3rd grade"})
            )
        assert exc.value.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("helped", [False, True])
async def test_saved_sorting_evidence_records_real_support_and_prior_feedback(helped):
    import json
    from unittest.mock import MagicMock

    from app.api.classrooms import Submission, save_response

    bp = blueprint()
    bp["scenes"][0]["type"] = "interactive"
    doc = {
        "format_version": CLASSROOM_VERSION,
        "phase": "ready",
        "blueprint": bp,
        "scenes": [sorting_scene(), *[scene(i) for i in range(1, 4)]],
        "canonical_slug": "matter",
        "responses": {"s0": {"text": "prior"}} if helped else {},
        "dialogue": {"s0": [{"key": "hint-1", "teaching_move": "scaffold"}]}
        if helped
        else {},
    }
    conn = AsyncMock()
    conn.transaction = MagicMock(return_value=AsyncMock())
    conn.fetchrow.side_effect = [{"id": "experience", "metadataJson": doc}, None]
    conn.fetchval.return_value = "attempt"
    with patch("app.api.classrooms.get_db_conn", new=AsyncMock(return_value=conn)):
        result = await save_response(
            "child",
            "unit",
            Submission(
                scene_id="s0",
                text='{"rock":"solid","water":"liquid"}',
                submission_key="attempt-1",
            ),
        )
    assert result["correct"]
    content = json.loads(conn.fetchval.await_args.args[5])
    assert content["previous_feedback_available"] is helped
    assert bool(content["support"]) is helped
    assert content["conditions"] == (
        "coach_conversation" if helped else "no_recorded_coach_support"
    )
    stored = json.loads(conn.execute.await_args.args[2])
    assert stored["responses"]["s0"]["text"] == '{"rock":"solid","water":"liquid"}'


@pytest.mark.asyncio
async def test_invalid_draft_is_sent_back_for_repair():
    import json
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from app.api import classrooms as api

    bad = scene(0)
    bad["id"] = "wrong-scene"
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=json.dumps(value)),
                        finish_reason="stop",
                    )
                ]
            )
            for value in [bad, scene(0)]
        ]
    )
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=client)
    manager.__aexit__ = AsyncMock(return_value=False)
    with (
        patch.object(api, "GEMINI_API_KEY", "test"),
        patch("openai.AsyncOpenAI", return_value=manager),
    ):
        result = await api.generate_json(
            "Teach.",
            Scene,
            {"requested_scene": blueprint()["scenes"][0], "blueprint": blueprint()},
        )
    assert result.id == "s0"
    messages = client.chat.completions.create.await_args.kwargs["messages"]
    assert json.loads(messages[-2]["content"])["id"] == "wrong-scene"
    assert "scene id and type" in messages[-1]["content"]


@pytest.mark.asyncio
async def test_provider_429_sets_cooldown_without_retrying():
    from unittest.mock import MagicMock

    import httpx
    import openai
    from app.api import classrooms as api
    from fastapi import HTTPException

    response = httpx.Response(
        429,
        headers={"retry-after": "120"},
        request=httpx.Request("POST", "https://provider.test"),
    )
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError(
            "Too many requests",
            response=response,
            body={"error": {"status": "RESOURCE_EXHAUSTED"}},
        )
    )
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=client)
    manager.__aexit__ = AsyncMock(return_value=False)
    with (
        patch.object(api, "GEMINI_API_KEY", "test"),
        patch.object(api, "_provider_retry_at", 0),
        patch("openai.AsyncOpenAI", return_value=manager),
    ):
        for _ in range(2):
            with pytest.raises(HTTPException) as exc:
                await api.generate_json("Plan.", Blueprint, {})
            assert exc.value.status_code == 503
            assert int(exc.value.headers["Retry-After"]) >= 119
        client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_does_not_wait_or_generate_when_other_worker_owns_it():
    from app.api import classrooms as api

    record = {
        "metadata": {"format_version": CLASSROOM_VERSION, "canonical_slug": "shared"}
    }
    conn = AsyncMock()
    conn.fetchval.return_value = False
    with (
        patch.object(api, "get_db_conn", AsyncMock(return_value=conn)),
        patch.object(
            api.student_experience_store, "get", AsyncMock(return_value=record)
        ),
        patch.object(api, "generate_json", AsyncMock()) as generate,
    ):
        await api.build_document("child", "unit")
    generate.assert_not_awaited()
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_build_request_returns_current_progress():
    import time

    from app.api import classrooms as api

    request = ClassroomRequest(
        topic="Mixtures", track=Track.CREATION_SCIENCE, action="build"
    )
    record = {
        "id": "copy",
        "title": "Mixtures",
        "metadata": {
            "format_version": CLASSROOM_VERSION,
            "phase": "building",
            "heartbeat": time.time(),
            "blueprint": blueprint(),
            "scenes": [],
        },
    }
    with (
        patch("app.services.rate_limit.enforce_rate_limit", AsyncMock()),
        patch.object(
            api.student_experience_store, "get", AsyncMock(return_value=record)
        ),
        patch.object(api.asyncio, "create_task") as create,
    ):
        result = await api.prepare_classroom("child", "unit", request)
    assert result["phase"] == "building"
    create.assert_not_called()


@pytest.mark.asyncio
async def test_gemini_throttle_uses_configured_openai_backup(monkeypatch):
    import json
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    import httpx
    import openai
    from app.api import classrooms as api

    monkeypatch.setattr(api, "GEMINI_API_KEY", "gemini-test")
    monkeypatch.setattr(api, "OPENAI_API_KEY", "openai-test")
    monkeypatch.setattr(api, "_provider_retry_at", 0)
    monkeypatch.setattr(api, "_fallback_retry_at", 0)
    response = httpx.Response(
        429, request=httpx.Request("POST", "https://provider.test")
    )
    primary = MagicMock()
    primary.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError("Quota", response=response, body={})
    )
    backup = MagicMock()
    backup.chat.completions.create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(blueprint())),
                    finish_reason="stop",
                )
            ]
        )
    )
    managers = []
    for client in [primary, backup]:
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=client)
        manager.__aexit__ = AsyncMock(return_value=False)
        managers.append(manager)
    with patch("openai.AsyncOpenAI", side_effect=managers):
        result = await api.generate_json("Teach.", Blueprint, {})
    assert result.title == "Mixtures"
    primary.chat.completions.create.assert_awaited_once()
    assert backup.chat.completions.create.await_args.kwargs["model"] == "gpt-4o-mini"
