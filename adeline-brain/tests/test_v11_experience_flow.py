"""Tests for the v11 experience-first authoring contract.

experience_design.flow is the authority over learner-facing sequence and
grouping; blocks[] remains the reusable content pool; layout is presentation
guidance only. Two independent validation layers exist on purpose:

- validate_flow_composition(): is there a real authored flow, do block
  references resolve, is every block accounted for. Structural only.
- validate_experience_substance(): does what the flow actually contains
  satisfy the experience being claimed. A flow can be structurally perfect
  and still fail here if every node points at a TEXT block.
"""
from app.curriculum.canonical_author import (
    CONTRACT_VERSION,
    EXPERIENCE_MODES,
    PROMPT_VERSION,
    CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT,
    validate_experience_substance,
    validate_flow_composition,
)
from app.curriculum.experience_contract import (
    ACTION_TYPES,
    CREATION_TYPES,
    DEMONSTRATION_TYPES,
    validate_experience,
)
from app.curriculum.family_style import CANONICAL_FORMAT_VERSION, is_current_family_canonical


def _block(block_id: str, block_type: str, evidence: list | None = None) -> dict:
    return {"block_id": block_id, "block_type": block_type, "evidence": evidence or []}


def _flow_node(node_id: str, *block_ids: str) -> dict:
    return {"node_id": node_id, "label": node_id, "block_ids": list(block_ids)}


# ── validate_flow_composition — structural checks only ────────────────────────

def test_flow_composition_requires_experience_design():
    assert validate_flow_composition({}) == ["experience_design is required"]


def test_flow_composition_requires_nonempty_flow():
    payload = {"experience_design": {"layout": "dossier"}}
    errors = validate_flow_composition(payload)
    assert any("flow must be a non-empty list" in e for e in errors)


def test_flow_composition_rejects_narrative_sequence_for_fresh_authoring():
    payload = {
        "experience_design": {"layout": "narrative_sequence", "flow": [_flow_node("a", "b1")]},
        "blocks": [_block("b1", "TEXT")],
    }
    errors = validate_flow_composition(payload)
    assert any("legacy read-only layout" in e for e in errors)


def test_flow_composition_rejects_unknown_layout():
    payload = {
        "experience_design": {"layout": "not_a_real_layout", "flow": [_flow_node("a", "b1")]},
        "blocks": [_block("b1", "TEXT")],
    }
    errors = validate_flow_composition(payload)
    assert any("supported composition layout" in e for e in errors)


def test_flow_composition_rejects_dangling_block_reference():
    payload = {
        "experience_design": {"layout": "dossier", "flow": [_flow_node("a", "b1", "b2")]},
        "blocks": [_block("b1", "TEXT")],  # b2 referenced but never authored
    }
    errors = validate_flow_composition(payload)
    assert any("unknown block_ids" in e and "b2" in e for e in errors)


def test_flow_composition_rejects_orphaned_block():
    payload = {
        "experience_design": {"layout": "dossier", "flow": [_flow_node("a", "b1")]},
        "blocks": [_block("b1", "TEXT"), _block("b2", "PRIMARY_SOURCE")],  # b2 never in flow
    }
    errors = validate_flow_composition(payload)
    assert any("not referenced by any flow node" in e and "b2" in e for e in errors)


def test_flow_composition_passes_when_every_block_is_referenced_exactly_once():
    payload = {
        "experience_design": {
            "layout": "lab_notebook",
            "flow": [_flow_node("opening", "b1"), _flow_node("experiment", "b2", "b3")],
        },
        "blocks": [_block("b1", "TEXT"), _block("b2", "EXPERIMENT"), _block("b3", "DATA_TRACKING")],
    }
    assert validate_flow_composition(payload) == []


# ── validate_experience_substance — the "flow isn't enough" guardrail ─────────

def test_all_text_flow_fails_substance_even_with_perfect_composition():
    """The exact case named in review: a structurally valid flow where every
    node points at TEXT. Must fail here even though validate_flow_composition
    would accept it cleanly."""
    payload = {
        "track": "DISCIPLESHIP",
        "experience_design": {
            "primary_mode": "investigation",
            "central_question": "What does this doctrine actually rest on?",
            "layout": "theology_map",
            "flow": [
                _flow_node("opening", "b1"),
                _flow_node("learn", "b2"),
                _flow_node("investigate", "b3"),
                _flow_node("analyze", "b4"),
            ],
        },
        "blocks": [
            _block("b1", "TEXT"), _block("b2", "TEXT"),
            _block("b3", "TEXT"), _block("b4", "TEXT"),
        ],
    }
    assert validate_flow_composition(payload) == []  # composition is fine
    errors = validate_experience_substance(payload)
    assert any("no component beyond TEXT/NARRATIVE" in e for e in errors)
    assert any("no genuine learner-action component" in e for e in errors)
    assert any("no genuine demonstration" in e for e in errors)


def test_investigation_family_requires_real_action_or_evidence_component():
    payload = {
        "track": "CREATIVE_ECONOMY",
        "experience_design": {
            "primary_mode": "family_project",
            "central_question": "How do we price handmade goods fairly?",
            "layout": "field_guide",
            "flow": [_flow_node("opening", "b1"), _flow_node("wrap", "b2")],
        },
        "blocks": [_block("b1", "TEXT"), _block("b2", "QUIZ")],
    }
    errors = validate_experience_substance(payload)
    assert any("substantive investigation or action" in e for e in errors)


def test_evidence_oriented_track_rejects_prose_describing_sources():
    payload = {
        "track": "TRUTH_HISTORY",
        "experience_design": {
            "primary_mode": "investigation",
            "central_question": "Did the railroads build America or capture it?",
            "layout": "dossier",
            "flow": [_flow_node("opening", "b1"), _flow_node("act", "b2"), _flow_node("show", "b3")],
        },
        "blocks": [
            _block("b1", "TEXT"),
            _block("b2", "DISCUSSION_FORUM"),
            _block("b3", "QUIZ"),
        ],
    }
    errors = validate_experience_substance(payload)
    assert any("actual routed PRIMARY_SOURCE" in e for e in errors)


def test_research_mission_cannot_replace_supplied_primary_evidence():
    payload = {
        "track": "JUSTICE_CHANGEMAKING",
        "experience_design": {
            "primary_mode": "public_interest_investigation",
            "central_question": "Who wrote the law?",
            "layout": "dossier",
            "flow": [_flow_node("opening", "b1"), _flow_node("research", "b2"), _flow_node("show", "b3")],
        },
        "blocks": [
            _block("b1", "TEXT"),
            _block("b2", "RESEARCH_MISSION"),
            _block("b3", "QUIZ"),
        ],
    }

    errors = validate_experience_substance(payload)

    assert any("actual routed PRIMARY_SOURCE" in error for error in errors)


def test_stem_requires_real_experiment_and_evidence_opportunity():
    # Claims an experiment but has none.
    no_experiment = {
        "track": "CREATION_SCIENCE",
        "experience_design": {
            "primary_mode": "stem",
            "central_question": "Why does the dough rise?",
            "layout": "lab_notebook",
            "flow": [_flow_node("opening", "b1"), _flow_node("act", "b2")],
        },
        "blocks": [_block("b1", "TEXT"), _block("b2", "DISCUSSION_FORUM")],
    }
    errors = validate_experience_substance(no_experiment)
    assert any("genuine EXPERIMENT or LAB_MISSION" in e for e in errors)

    # Has an experiment block but it carries no evidence/observation.
    no_evidence = {
        "track": "CREATION_SCIENCE",
        "experience_design": {
            "primary_mode": "stem",
            "central_question": "Why does the dough rise?",
            "layout": "lab_notebook",
            "flow": [_flow_node("opening", "b1"), _flow_node("act", "b2")],
        },
        "blocks": [_block("b1", "TEXT"), _block("b2", "EXPERIMENT")],  # evidence=[] by default
    }
    errors = validate_experience_substance(no_evidence)
    assert any("evidence/observation opportunity" in e for e in errors)

    # Real experiment with a real observation opportunity — passes.
    good = {
        "track": "CREATION_SCIENCE",
        "experience_design": {
            "primary_mode": "stem",
            "central_question": "Why does the dough rise?",
            "layout": "lab_notebook",
            "flow": [_flow_node("opening", "b1"), _flow_node("act", "b2"), _flow_node("show", "b3")],
        },
        "blocks": [
            _block("b1", "TEXT"),
            _block("b2", "EXPERIMENT", evidence=[{"type": "measurement", "prompt": "rise height every 30 min"}]),
            _block("b3", "QUIZ"),
        ],
    }
    assert validate_experience_substance(good) == []


def test_skill_practice_requires_genuine_problems_not_explanation_alone():
    explanation_only = {
        "track": "APPLIED_MATHEMATICS",
        "experience_design": {
            "primary_mode": "skill_practice",
            "central_question": "Multiplying fractions",
            "layout": "skill_ladder",
            "flow": [_flow_node("opening", "b1"), _flow_node("recap", "b2")],
        },
        "blocks": [_block("b1", "TEXT"), _block("b2", "TEXT")],
    }
    errors = validate_experience_substance(explanation_only)
    assert any("genuine learner problems/tasks/practice" in e for e in errors)

    real_practice = {
        "track": "APPLIED_MATHEMATICS",
        "experience_design": {
            "primary_mode": "skill_practice",
            "central_question": "Multiplying fractions",
            "layout": "skill_ladder",
            "flow": [_flow_node("opening", "b1"), _flow_node("practice", "b2"), _flow_node("check", "b3")],
        },
        "blocks": [_block("b1", "TEXT"), _block("b2", "PROBLEM"), _block("b3", "QUIZ")],
    }
    assert validate_experience_substance(real_practice) == []


def test_central_question_is_required():
    payload = {
        "track": "CREATION_SCIENCE",
        "experience_design": {
            "primary_mode": "stem",
            "layout": "lab_notebook",
            "flow": [_flow_node("opening", "b1"), _flow_node("act", "b2"), _flow_node("show", "b3")],
        },
        "blocks": [
            _block("b1", "TEXT"),
            _block("b2", "EXPERIMENT", evidence=[{"type": "measurement"}]),
            _block("b3", "QUIZ"),
        ],
    }
    errors = validate_experience_substance(payload)
    assert any("real central question or skill target" in e for e in errors)


# ── skill_practice is a real supported mode ────────────────────────────────────

def test_skill_practice_is_a_supported_experience_mode():
    assert "skill_practice" in EXPERIENCE_MODES


# ── stage/type consistency (closes the self-labeling gap) ─────────────────────

def test_genui_assembly_is_flexible_across_action_creation_demonstration():
    assert "GENUI_ASSEMBLY" in ACTION_TYPES
    assert "GENUI_ASSEMBLY" in CREATION_TYPES
    assert "GENUI_ASSEMBLY" in DEMONSTRATION_TYPES


def test_text_block_cannot_satisfy_action_by_self_labeling_stage():
    blocks = [
        {"block_type": "TEXT", "experience_stage": "INVITATION", "content": "..."},
        {"block_type": "TEXT", "experience_stage": "ACTION", "content": "..."},  # mislabeled
        {"block_type": "QUIZ", "experience_stage": "DEMONSTRATION", "content": "..."},
    ]
    errors = validate_experience(blocks)
    assert any("cannot satisfy that stage" in e and "ACTION" in e for e in errors)


def test_experiment_block_can_legitimately_satisfy_action_stage():
    blocks = [
        {"block_type": "TEXT", "experience_stage": "INVITATION", "content": "..."},
        {"block_type": "EXPERIMENT", "experience_stage": "ACTION", "content": "..."},
        {"block_type": "QUIZ", "experience_stage": "DEMONSTRATION", "content": "..."},
    ]
    errors = validate_experience(blocks)
    assert not any("cannot satisfy that stage" in e for e in errors)


# ── format-version floor: legacy content stays servable ────────────────────────

def test_legacy_v10_and_current_v11_canonicals_are_both_servable():
    v10_block = {"family_style": True, "canonical_format_version": 10}
    v11_block = {"family_style": True, "canonical_format_version": 11}
    pre_family_style_block = {"family_style": True, "canonical_format_version": 9}

    assert CANONICAL_FORMAT_VERSION == 11
    assert is_current_family_canonical([v10_block]), "legacy pre-flow canonicals must stay servable from cache"
    assert is_current_family_canonical([v11_block])
    assert not is_current_family_canonical([pre_family_style_block])


# ── version metadata exists and is real ────────────────────────────────────────

def test_contract_and_prompt_version_are_real_nonempty_strings():
    assert isinstance(CONTRACT_VERSION, str) and CONTRACT_VERSION.strip()
    assert isinstance(PROMPT_VERSION, str) and PROMPT_VERSION.strip()


def test_prompt_teaches_flow_ownership_and_substance_requirements():
    prompt = CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT
    assert "experience_design.flow is the actual order" in prompt
    assert "never determines what content exists or its order" in prompt
    assert "is not" in prompt and "meaningfully different from a lesson with no flow at all" in prompt
    assert "skill_practice" in prompt
