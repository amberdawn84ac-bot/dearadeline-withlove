"""Autonomous per-class rubrics: contracts and safe, evidence-based feedback."""

import json

import pytest
from pydantic import ValidationError

from app.api.classrooms import validate_draft
from app.curriculum.classroom import (
    Blueprint,
    ClassRubric,
    RUBRIC_CONTRACT_REVISION,
)
from app.services.classroom_assessment import (
    RubricReview,
    checked_rubric_review,
)


def criterion(id="reasoning"):
    return {
        "id": id,
        "focus": "Explain the actual ratio relationship",
        "evidence": "An explanation of proportional comparison using a fresh numerical example.",
        "emerging": "Names amounts but does not establish the comparison.",
        "developing": "Identifies a relationship but cannot justify scaling.",
        "proficient": "Uses a fresh example to justify multiplicative scaling.",
        "advanced": "Explains why scaling works and where it cannot be used.",
    }


def rubric():
    return {
        "purpose": "Evaluate a learner's independent reasoning in a ratio investigation.",
        "criteria": [criterion(), {**criterion("transfer"), "focus": "Transfer reasoning to a new case"}],
    }


def test_rubric_requires_distinct_specific_performance_levels():
    assert len(ClassRubric.model_validate(rubric()).criteria) == 2
    bad = rubric()
    bad["criteria"][0]["advanced"] = bad["criteria"][0]["proficient"]
    with pytest.raises(ValidationError, match="distinct descriptor"):
        ClassRubric.model_validate(bad)


def test_new_blueprint_cannot_omit_either_generated_rubric():
    data = {
        "title": "Real ratios",
        "understanding": "Ratios express multiplicative comparisons.",
        "essential_question": "How can we compare fairly?",
        "demonstration": "Justify a new proportional comparison.",
        "integrated_tracks": ["APPLIED_MATHEMATICS"],
        "roster": [
            {"id": "adeline", "name": "Adeline", "role": "teacher", "persona": "Teaches through evidence."},
            {"id": "peer", "name": "Peer", "role": "assistant", "persona": "Asks useful questions."},
        ],
        "scenes": [
            {"id": str(i), "title": "Ratio", "type": "quiz" if i == 3 else "slide",
             "objective": "Explain how ratios work.", "brief": "Analyze a concrete ratio example."}
            for i in range(4)
        ],
        "next_revisit": "Compare ratios using proportional graphs next.",
    }
    # Past documents remain readable, but new authored drafts must generate both.
    blueprint = Blueprint.model_validate(data)
    with pytest.raises(ValueError, match="both class_quality_rubric and mastery_rubric"):
        validate_draft(
            Blueprint, blueprint.model_dump_json(),
            {"rubric_contract": RUBRIC_CONTRACT_REVISION, "track": "APPLIED_MATHEMATICS"},
        )


def test_feedback_downgrades_unverified_or_supported_claims():
    data = rubric()
    work = {"text": "When both quantities double the comparison stays the same."}
    review = RubricReview.model_validate({
        "observations": [
            {"criterion_id": id, "level": "proficient",
             "evidence_quote": work["text"],
             "explanation": "This directly describes how the two quantities change.",
             "next_step": "Test whether that relationship survives a new example."}
            for id in ("reasoning", "transfer")
        ]
    })
    assert all(
        item["level"] == "insufficient_evidence"
        for item in checked_rubric_review(review, data, work, independent=False)
    )
    assert all(
        item["level"] == "proficient"
        for item in checked_rubric_review(review, data, work, independent=True)
    )
    with pytest.raises(ValueError, match="quote"):
        checked_rubric_review(
            review.model_copy(update={"observations": [
                review.observations[0].model_copy(update={"evidence_quote": "Invented quote"}),
                review.observations[1],
            ]}), data, work, independent=True,
        )
