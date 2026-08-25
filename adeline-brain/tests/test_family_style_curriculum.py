from app.curriculum.family_style import (
    CANONICAL_FORMAT_VERSION,
    FAMILY_CANONICAL_AUTHORING_RULES,
    finalize_family_lesson,
    is_current_family_canonical,
)
from app.agents.adapter import sanitize_learner_text


def test_canonical_rules_keep_truth_fixed_while_roles_change():
    assert "full-depth and durable" in FAMILY_CANONICAL_AUTHORING_RULES
    assert "siblings do not receive cloned work" in FAMILY_CANONICAL_AUTHORING_RULES
    assert "button clicks are never mastery" in FAMILY_CANONICAL_AUTHORING_RULES


def test_only_current_family_canonicals_are_reused():
    current = {
        "block_type": "TEXT",
        "content": "Water moves through a watershed.",
        "family_style": True,
        "canonical_format_version": CANONICAL_FORMAT_VERSION,
    }
    assert is_current_family_canonical([current])
    assert not is_current_family_canonical([{**current, "canonical_format_version": 1}])


def test_finalizer_preserves_structure_and_removes_obsolete_rebuilders():
    blocks = [
        {"block_type": "NARRATIVE", "experience_stage": "INVITATION", "content": "A complete explanation."},
        {"block_type": "NARRATIVE", "experience_stage": "INVITATION", "content": "A complete explanation."},
        {"block_type": "NARRATED_SLIDE", "content": "An obsolete slide rebuild."},
        {"block_type": "ANIMATED_SKETCHNOTE_LESSON", "content": "An obsolete animation rebuild."},
        {"block_type": "GENUI_ASSEMBLY", "content": "Malformed widget."},
        {
            "block_type": "GENUI_ASSEMBLY",
            "experience_stage": "CREATION",
            "content": "A real project.",
            "genui_assembly_data": {"component_type": "ProjectBuilder", "props": {"title": "Build"}},
        },
        {"block_type": "TEXT", "experience_stage": "DISCOVERY", "content": "Measure the material."},
        {"block_type": "REAL_WORLD_APP", "experience_stage": "ACTION", "content": "Build the useful object."},
        {"block_type": "QUIZ", "experience_stage": "DEMONSTRATION", "content": "Check the plan."},
        {"block_type": "TEXT", "experience_stage": "REFLECTION", "content": "Record the result."},
    ]

    finalized = finalize_family_lesson(blocks, "Woodworking", track="CREATIVE_ECONOMY")

    assert [block["block_type"] for block in finalized] == [
        "NARRATIVE", "GENUI_ASSEMBLY", "TEXT", "REAL_WORLD_APP", "QUIZ", "TEXT",
    ]
    assert all(block["canonical_format_version"] == CANONICAL_FORMAT_VERSION for block in finalized)
    assert {block["experience_stage"] for block in finalized} >= {
        "INVITATION", "ACTION", "DEMONSTRATION",
    }


def test_learner_text_removes_internal_notes_and_identity_errors():
    content = (
        "Your job, Adeline, is to explain what God says.\n\n"
        "[GENUI hint: a quiz block after this content would reinforce foundation.]"
    )

    cleaned = sanitize_learner_text(content)

    assert cleaned == "Your job is to explain what HaShem says."


def _truth_history_blocks(evidence: list[dict]) -> list[dict]:
    return [
        {"block_type": "TEXT", "experience_stage": "INVITATION", "content": "Which story does the record support?"},
        {
            "block_type": "PRIMARY_SOURCE",
            "experience_stage": "DISCOVERY",
            "content": "Examine the original record before reading later interpretations.",
            "evidence": evidence,
        },
        {"block_type": "TIMELINE", "experience_stage": "CREATION", "content": "Place and source the event on the living wall timeline."},
        {"block_type": "RESEARCH_MISSION", "experience_stage": "ACTION", "content": "Corroborate the record with an independent source."},
        {"block_type": "QUIZ", "experience_stage": "DEMONSTRATION", "content": "Defend what the evidence establishes and what remains uncertain."},
    ]


def test_truth_history_requires_traceable_outside_primary_evidence_and_timeline():
    evidence = [{
        "source_title": "Interstate Commerce Commission report",
        "holding_institution": "U.S. National Archives",
        "source_url": "https://catalog.archives.gov/id/123",
    }]

    finalized = finalize_family_lesson(
        _truth_history_blocks(evidence), "Railroads and Power", track="TRUTH_HISTORY"
    )

    assert any(block["block_type"] == "PRIMARY_SOURCE" for block in finalized)
    assert any(block["block_type"] == "TIMELINE" for block in finalized)


def test_truth_history_rejects_model_paraphrase_as_primary_evidence():
    finalized = finalize_family_lesson(
        _truth_history_blocks([{"source_title": "A source-like summary"}]),
        "Railroads and Power",
        track="TRUTH_HISTORY",
    )

    assert finalized == []
