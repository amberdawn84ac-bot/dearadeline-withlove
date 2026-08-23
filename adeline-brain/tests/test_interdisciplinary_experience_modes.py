from app.agents.adapter import AdaptationRequest
from app.curriculum.canonical_author import CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT, validate_canonical_contract
from app.curriculum.family_style import CANONICAL_FORMAT_VERSION, FAMILY_CANONICAL_AUTHORING_RULES
from app.services.learner_context import learner_contribution


def test_one_generator_owns_interdisciplinary_modes():
    prompt = CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT.lower()
    assert CANONICAL_FORMAT_VERSION == 8
    for mode in ("stem", "steam", "arts_integrated", "maker_build", "design_challenge"):
        assert mode in prompt
    assert "not separate subjects, generators, portals" in FAMILY_CANONICAL_AUTHORING_RULES.lower()
    assert "random arithmetic" in prompt
    assert "decoration to claim steam" in prompt


def test_learner_contribution_preserves_process_product_and_cross_track_evidence():
    contract = {
        "experience_design": {
            "primary_mode": "design_challenge",
            "learner_facing_choices": ["build and test", "model and explain"],
        },
        "portfolio_task": {
            "process_evidence": ["design sketch", "measurements"],
            "product_evidence": ["working prototype"],
            "failure_and_revision_evidence": ["failed test and redesign note"],
        },
        "mastery_evidence_map": [{
            "concept": "forces",
            "discipline_or_track": "CREATION_SCIENCE",
            "acceptable_evidence": ["test data and explanation"],
            "must_be_demonstrated_by_individual": True,
            "not_awarded_for_exposure_alone": True,
        }],
    }
    adaptation = AdaptationRequest(grade_level="6", track="CREATION_SCIENCE")

    contribution = learner_contribution(contract, adaptation)

    assert contribution["experience_mode"] == "design_challenge"
    assert contribution["learner_facing_choices"] == ["build and test", "model and explain"]
    assert contribution["evidence_to_preserve"]["process"] == ["design sketch", "measurements"]
    assert contribution["evidence_to_preserve"]["failure_and_revision"]
    assert contribution["mastery_evidence_map"][0]["not_awarded_for_exposure_alone"] is True


def test_contract_rejects_decorative_steam_and_exposure_credit():
    payload = {
        "experience_design": {
            "primary_mode": "steam",
            "disciplines_integrated": ["science", "art"],
            "integration_rationale": "",
            "constraints": [],
        },
        "portfolio_task": {},
        "mastery_evidence_map": [{
            "concept": "wave frequency",
            "acceptable_evidence": [],
            "not_awarded_for_exposure_alone": False,
        }],
    }

    errors = validate_canonical_contract(payload)

    assert any("integration is meaningful" in error for error in errors)
    assert any("genuine constraint" in error for error in errors)
    assert any("observable process or product" in error for error in errors)
    assert any("observable evidence" in error for error in errors)
    assert any("exposure alone" in error for error in errors)
