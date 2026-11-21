"""The class quality gate must not publish a failed lesson."""
from unittest.mock import AsyncMock

import pytest

from app.curriculum.classroom import Blueprint, Scene
from app.curriculum.classroom_review import (
    QualityReview, checked_review, review_and_repair,
)
def basic_blueprint():
    return {
        "title": "Mixtures",
        "understanding": "Ratios compare quantities multiplicatively.",
        "essential_question": "How can we compare mixtures?",
        "demonstration": "Compare and explain two new mixtures.",
        "integrated_tracks": ["CREATION_SCIENCE", "APPLIED_MATHEMATICS"],
        "roster": [
            {"id": "adeline", "name": "Adeline", "role": "teacher",
             "persona": "Warm, knowledgeable mentor."},
            {"id": "peer", "name": "Colleague", "role": "assistant",
             "persona": "Asks for evidence and clarification."},
        ],
        "scenes": [
            {"id": f"s{i}", "title": f"Compare mixture {i}",
             "type": "quiz" if i == 3 else "slide",
             "objective": "Explain the quantities.",
             "brief": "Show a concrete example and explain it."}
            for i in range(4)
        ],
        "next_revisit": "Connect ratios to graphs in another context.",
    }


def basic_scene(i):
    scene = {
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
    }
    if i == 3:
        scene["question"] = {
            "prompt": "Which equals 1:2?",
            "choices": [
                {"id": "a", "label": "2:4"},
                {"id": "b", "label": "2:3"},
            ],
            "answer": "a",
            "explanation": "Multiplying both amounts by two preserves the ratio.",
        }
    return scene



def reviewed_blueprint():
    data = basic_blueprint()
    data["class_quality_rubric"] = {
        "purpose": "Evaluate whether this ratio lesson actually explains and tests reasoning.",
        "criteria": [
            {
                "id": id,
                "focus": focus,
                "evidence": "A worked ratio explanation and task where independent work is visible.",
                "emerging": "Only mentions a comparison without an example.",
                "developing": "Shows a ratio without explaining why scaling works.",
                "proficient": "Explains proportional scaling and asks for a new use.",
                "advanced": "Shows a new transfer case and explains the model boundary.",
            }
            for id, focus in [
                ("accuracy", "Explanation uses accurate ratio reasoning"),
                ("practice", "Practice includes observable independent reasoning"),
            ]
        ],
    }
    return Blueprint.model_validate(data)


def review(verdict="pass"):
    return QualityReview.model_validate({
        "findings": [
            {
                "criterion_id": id,
                "scene_id": "s0",
                "verdict": verdict if id == "accuracy" else "pass",
                "observation": "The ratio explanation does not show how scaling works.",
                "revision": "Add an explicit worked 1:2 to 2:4 scaling explanation."
                if verdict == "revise" and id == "accuracy" else None,
            }
            for id in ("accuracy", "practice")
        ]
    })


def test_review_validates_rubric_coverage_and_real_scene_ids():
    bp = reviewed_blueprint()
    assert checked_review(review(), bp) == {}
    failures = checked_review(review("revise"), bp)
    assert failures["s0"][0].startswith("accuracy:")
    bad = review().model_dump()
    bad["findings"][1]["criterion_id"] = "accuracy"
    with pytest.raises(ValueError, match="every class-quality criterion"):
        checked_review(QualityReview.model_validate(bad), bp)
    bad = review().model_dump()
    bad["findings"][0]["scene_id"] = "invented"
    with pytest.raises(ValueError, match="real scene"):
        checked_review(QualityReview.model_validate(bad), bp)


@pytest.mark.asyncio
async def test_revises_a_failed_scene_then_rechecks_before_publication():
    bp = reviewed_blueprint()
    scenes = [Scene.model_validate(basic_scene(i)) for i in range(4)]
    improved = scenes[0].model_copy(update={"content": "A 1:2 ratio scales to 2:4 by multiplying both quantities by two."})
    generate = AsyncMock(side_effect=[review("revise"), improved, review()])
    persist = AsyncMock()
    seen_contexts = []

    def context(brief, earlier, diagnostic):
        seen_contexts.append(diagnostic)
        return {"requested_scene": brief.model_dump(), "blueprint": bp.model_dump()}

    updated, audit = await review_and_repair(
        bp, scenes, generate=generate, make_scene_context=context,
        on_repair=persist,
    )
    assert updated[0].content == improved.content
    assert len(seen_contexts) == 1
    assert "scaling" in seen_contexts[0]
    assert generate.await_count == 3
    persist.assert_awaited_once()
    assert audit["findings"][0]["verdict"] == "pass"


@pytest.mark.asyncio
async def test_unresolved_quality_gaps_fail_closed():
    bp = reviewed_blueprint()
    scenes = [Scene.model_validate(basic_scene(i)) for i in range(4)]
    generate = AsyncMock(side_effect=[review("revise"), scenes[0], review("revise")])
    with pytest.raises(ValueError, match="instructional gaps"):
        await review_and_repair(
            bp, scenes, generate=generate,
            make_scene_context=lambda brief, previous, text: {
                "requested_scene": brief.model_dump(),
                "blueprint": bp.model_dump(),
            },
            on_repair=AsyncMock(),
        )
