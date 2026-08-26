from app.agents.adapter import AdaptationRequest
from app.curriculum.canonical_author import (
    CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT,
    enforce_non_exposure_mastery,
    validate_canonical_contract,
)
from app.curriculum.family_style import CANONICAL_FORMAT_VERSION, FAMILY_CANONICAL_AUTHORING_RULES
from app.services.learner_context import learner_contribution


def test_one_generator_owns_interdisciplinary_modes():
    prompt = CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT.lower()
    assert CANONICAL_FORMAT_VERSION == 11
    for mode in ("stem", "steam", "arts_integrated", "maker_build", "design_challenge"):
        assert mode in prompt
    assert "not separate subjects, generators, portals" in FAMILY_CANONICAL_AUTHORING_RULES.lower()
    assert "random arithmetic" in prompt
    assert "decoration to claim steam" in prompt


def test_learner_contribution_preserves_process_product_and_cross_track_evidence():
    contract = {
        "experience_design": {
            "primary_mode": "design_challenge",
            "entry_move": "Inspect two failed bridge models and test their load limits.",
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
            "entry_move": "Listen to and visualize two wave frequencies.",
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


def test_author_normalization_enforces_non_exposure_policy_only():
    payload = {
        "mastery_evidence_map": [{
            "concept": "Federal subsidy and corporate power",
            "acceptable_evidence": ["A claim tied to two primary records"],
            "not_awarded_for_exposure_alone": False,
        }],
    }

    normalized = enforce_non_exposure_mastery(payload)

    assert normalized["mastery_evidence_map"][0]["not_awarded_for_exposure_alone"] is True
    assert normalized["mastery_evidence_map"][0]["acceptable_evidence"] == [
        "A claim tied to two primary records"
    ]


def test_public_interest_work_requires_records_claim_discipline_and_real_agency():
    payload = {
        "experience_design": {
            "primary_mode": "public_interest_investigation",
            "entry_move": "Compare a company advertisement with a regulatory filing.",
            "disciplines_integrated": ["public health", "government", "justice"],
            "integration_rationale": "The policy outcome depends on all three.",
        },
        "public_interest_contract": {
            "power_and_accountability_question": "",
            "primary_record_types": [],
            "industry_system_map": {},
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
    assert any("profit and incentives" in error for error in errors)
    assert any("institutions and decision-makers" in error for error in errors)
    assert any("distinguish facts" in error for error in errors)
    assert any("validated need" in error for error in errors)


def test_prompt_rejects_project_theater_and_maps_food_industries_as_systems():
    prompt = CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT.lower()
    assert "lesson about project-based learning" in prompt
    assert "predetermined \"correct\" opinions" in prompt
    assert "ownership, supply chains, revenue" in prompt
    assert "verify health and toxicity claims" in prompt
    assert "industry_system_map" in prompt


def test_public_action_requires_stakeholder_validation_and_impact_feedback():
    payload = {
        "experience_design": {
            "primary_mode": "civic_action_project",
            "entry_move": "Ask a local pantry what information or service would actually help.",
            "disciplines_integrated": ["food systems", "civics"],
            "integration_rationale": "The pantry need is shaped by both supply and policy.",
        },
        "public_interest_contract": {
            "power_and_accountability_question": "Who controls access and funding?",
            "primary_record_types": ["public budgets"],
            "claim_distinctions": ["verified_fact", "allegation", "legal_finding", "unanswered_question"],
            "industry_system_map": {
                "profit_and_incentive_question": "Who benefits from the current allocation?",
                "institutions_and_decision_makers_to_trace": ["county board", "supplier"],
            },
            "live_action_options": [{
                "action": "Create a requested resource",
                "real_recipient": "local pantry",
                "intended_change": "reduce a documented information gap",
                "stakeholder_need_validation": "",
                "feedback_or_impact_signal": "",
            }],
        },
        "portfolio_task": {"process_evidence": ["stakeholder notes"]},
        "mastery_evidence_map": [{
            "concept": "public resource allocation",
            "acceptable_evidence": ["budget-supported explanation"],
            "not_awarded_for_exposure_alone": True,
        }],
    }

    errors = validate_canonical_contract(payload)

    assert any("validated need" in error and "impact signal" in error for error in errors)


def test_truth_history_builds_an_evidence_led_living_wall_timeline():
    prompt = CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT.lower()
    assert "living wall timeline" in prompt
    assert "printable and cut-out friendly" in prompt
    assert "common story / what the record supports" in prompt
    assert "propaganda" in prompt
    assert "people or perspectives commonly left out" in prompt
    assert "disputed dates" in prompt
    assert "unsupported counter-myth" in prompt
    assert "not a decoration or memorization strip" in prompt
