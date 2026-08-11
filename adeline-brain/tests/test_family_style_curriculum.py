from app.curriculum.family_style import (
    FAMILY_CANONICAL_AUTHORING_RULES,
    ensure_family_workshop,
    family_workshop_block,
)
from app.agents.adapter import sanitize_learner_text


def test_family_workshop_has_shared_work_roles_and_portfolio_evidence():
    block = family_workshop_block("Children Who Changed History")

    assert block["family_style"] is True
    assert "Make one real thing together" in block["content"]
    assert "grades 4–5" in block["content"]
    assert "grades 6–8" in block["content"]
    assert "grades 9–12" in block["content"]
    assert "portfolio evidence" in block["content"]


def test_ensure_family_workshop_is_idempotent():
    original = [{"block_type": "NARRATIVE", "content": "Truth."}]
    once = ensure_family_workshop(original, "A topic")
    twice = ensure_family_workshop(once, "A topic")

    assert len(original) == 1
    assert len(once) == 2
    assert twice == once


def test_canonical_rules_keep_truth_fixed_while_roles_change():
    assert "full adult/high-school depth" in FAMILY_CANONICAL_AUTHORING_RULES
    assert "different responsibility" in FAMILY_CANONICAL_AUTHORING_RULES
    assert "facts, sources, central questions, and worldview fixed" in FAMILY_CANONICAL_AUTHORING_RULES


def test_learner_text_removes_internal_notes_and_identity_errors():
    content = (
        "Your job, Adeline, is to explain what God says.\n\n"
        "[GENUI hint: a quiz block after this content would reinforce foundation.]"
    )

    cleaned = sanitize_learner_text(content)

    assert cleaned == "Your job is to explain what HaShem says."
