from app.agents.persona import ADELINE_SYSTEM_PROMPT, SCRIPTURE_TRANSLATION_POLICY


def test_scripture_policy_preserves_original_names_and_sources():
    policy = SCRIPTURE_TRANSLATION_POLICY

    assert "YHWH" in policy
    assert "Elohim" in policy
    assert "Yeshua" in policy
    assert "Masoretic Hebrew text" in policy
    assert "earliest critically attested Greek" in policy
    assert "Everett Fox" in policy


def test_scripture_policy_does_not_treat_modern_translation_as_controlling():
    policy = SCRIPTURE_TRANSLATION_POLICY

    assert "KJV" in policy
    assert "NIV" in policy
    assert "controlling text" in policy
    assert "what is documented, what is disputed, and what remains" in policy
    assert "do not call a suspicion proven without evidence" in policy


def test_top_level_persona_includes_scripture_policy():
    assert SCRIPTURE_TRANSLATION_POLICY in ADELINE_SYSTEM_PROMPT
