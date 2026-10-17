from copy import deepcopy
from unittest.mock import AsyncMock, patch
import pytest
from pydantic import ValidationError
from app.curriculum.classroom import (
    Blueprint,
    Scene,
    Classroom,
    public_classroom,
    CLASSROOM_VERSION,
)
from app.api.classrooms import (
    ClassroomRequest,
    classroom_slug,
    public_state,
    build_document,
)
from app.schemas.api_models import Track
from app.agents.persona import ADELINE_CLASSROOM_PERSONA


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
    from app.curriculum.builtin_canonicals import builtin_canonical
    from app.jobs.canonical_seeding import canonical_seeding_enabled
    from app.api.classrooms import document_from

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
                    message=SimpleNamespace(content=json.dumps(blueprint()))
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
