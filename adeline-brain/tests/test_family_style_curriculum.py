from app.curriculum.family_style import (
    CANONICAL_FORMAT_VERSION,
    FAMILY_CANONICAL_AUTHORING_RULES,
    ensure_family_workshop,
    finalize_family_lesson,
    family_workshop_block,
    is_current_family_canonical,
)
from app.agents.adapter import sanitize_learner_text


def test_family_workshop_helper_is_explicitly_deprecated():
    block = family_workshop_block("Children Who Changed History")

    assert block["family_style"] is True
    assert block["deprecated"] is True
    assert block["canonical_format_version"] == CANONICAL_FORMAT_VERSION


def test_ensure_family_workshop_is_idempotent():
    original = [{"block_type": "NARRATIVE", "content": "Truth."}]
    once = ensure_family_workshop(original, "A topic")
    twice = ensure_family_workshop(once, "A topic")

    assert len(original) == 1
    assert len(once) == 1
    assert twice == once


def test_canonical_rules_keep_truth_fixed_while_roles_change():
    assert "full adult/high-school depth" in FAMILY_CANONICAL_AUTHORING_RULES
    assert "different responsibility" in FAMILY_CANONICAL_AUTHORING_RULES
    assert "central question, learning goal, verified facts" in FAMILY_CANONICAL_AUTHORING_RULES


def test_only_current_family_canonicals_are_reused():
    current = {
        "block_type": "TEXT",
        "content": "Water moves through a watershed.",
        "family_style": True,
        "canonical_format_version": CANONICAL_FORMAT_VERSION,
    }
    assert is_current_family_canonical([current])
    assert not is_current_family_canonical([{**current, "canonical_format_version": 1}])
    assert not is_current_family_canonical([family_workshop_block("Water")])


def test_finalizer_preserves_structure_and_removes_obsolete_rebuilders():
    blocks = [
        {"block_type": "NARRATIVE", "content": "A complete explanation."},
        {"block_type": "NARRATIVE", "content": "A complete explanation."},
        {"block_type": "NARRATED_SLIDE", "content": "An obsolete slide rebuild."},
        {"block_type": "ANIMATED_SKETCHNOTE_LESSON", "content": "An obsolete animation rebuild."},
        {"block_type": "GENUI_ASSEMBLY", "content": "Malformed widget."},
        {
            "block_type": "GENUI_ASSEMBLY",
            "content": "A real project.",
            "genui_assembly_data": {"component_type": "ProjectBuilder", "props": {"title": "Build"}},
        },
        {"block_type": "TEXT", "content": "Measure the material."},
        {"block_type": "REAL_WORLD_APP", "content": "Build the useful object."},
        {"block_type": "QUIZ", "content": "Check the plan."},
        {"block_type": "TEXT", "content": "Record the result."},
    ]

    finalized = finalize_family_lesson(blocks, "Woodworking", track="CREATIVE_ECONOMY")

    assert [block["block_type"] for block in finalized] == [
        "NARRATIVE", "GENUI_ASSEMBLY", "TEXT", "REAL_WORLD_APP", "QUIZ", "TEXT",
    ]
    assert all(block["canonical_format_version"] == CANONICAL_FORMAT_VERSION for block in finalized)


def test_learner_text_removes_internal_notes_and_identity_errors():
    content = (
        "Your job, Adeline, is to explain what God says.\n\n"
        "[GENUI hint: a quiz block after this content would reinforce foundation.]"
    )

    cleaned = sanitize_learner_text(content)

    assert cleaned == "Your job is to explain what HaShem says."
