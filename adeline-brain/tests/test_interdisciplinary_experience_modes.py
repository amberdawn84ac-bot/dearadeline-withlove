from app.agents.adapter import AdaptationRequest
from app.curriculum.canonical_author import CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT, validate_canonical_contract
from app.curriculum.family_style import CANONICAL_FORMAT_VERSION, FAMILY_CANONICAL_AUTHORING_RULES
from app.services.learner_context import learner_contribution


def test_one_generator_owns_interdisciplinary_modes():
    prompt = CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT.lower()
    assert CANONICAL_FORMAT_VERSION == 9
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


def test_public_interest_work_requires_records_claim_discipline_and_real_agency():
    payload = {
        "experience_design": {
            "primary_mode": "public_interest_investigation",
            "disciplines_integrated": ["public health", "government", "justice"],
            "integration_rationale": "The policy outcome depends on all three.",
        },
        "public_interest_contract": {
            "power_and_accountability_question": "",
            "primary_record_types": [],
            "claim_distinctions": ["verified_fact"],
            "live_action_options": [{"action": "make a poster"}],
        },
        "portfolio_task": {"process_evidence": ["source reliability table"]},
        "mastery_evidence_map": [{
            "concept": "civil and criminal accountability",
            "acceptable_evidence": ["comparison supported by court records and statutes"],
            "not_awarded_for_exposure_alone": True,
        }],
    }

    errors = validate_canonical_contract(payload)

    assert any("primary records" in error for error in errors)
    assert any("power and accountability" in error for error in errors)
    assert any("distinguish facts" in error for error in errors)
    assert any("real recipient" in error for error in errors)
