from app.agents.persona import ADELINE_SYSTEM_PROMPT, SCRIPTURE_TRANSLATION_POLICY
from app.curriculum.canonical_author import CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT


def test_scripture_policy_preserves_original_names_and_sources():
    policy = SCRIPTURE_TRANSLATION_POLICY

    assert "YHWH" in policy
    assert "Elohim" in policy
    assert "Yeshua" in policy
    assert "Masoretic Hebrew text" in policy
    assert "earliest critically attested Greek" in policy
    assert "Everett Fox" in policy


def test_scripture_policy_his_name_is_not_god():
    policy = SCRIPTURE_TRANSLATION_POLICY

    assert 'His name is not "God."' in policy
    assert "Original names, meaning, and context always" in policy
    assert "never a generic \"God's design.\"" in policy
    assert "Point out when translating into English caused a loss" in policy
    assert "Point out when someone purposefully changed something" in policy
    assert "Do not treat suspicion as proof" in policy


def test_scripture_policy_does_not_treat_modern_translation_as_controlling():
    policy = SCRIPTURE_TRANSLATION_POLICY

    assert "KJV" in policy
    assert "NIV" in policy
    assert "controlling text" in policy
    assert "what is documented, what is disputed, and what remains" in policy
    assert "do not call a suspicion proven without evidence" in policy


def test_top_level_persona_includes_scripture_policy():
    assert SCRIPTURE_TRANSLATION_POLICY in ADELINE_SYSTEM_PROMPT


def test_canonical_author_uses_original_names_not_english_substitutes():
    prompt = CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT

    assert "His name is not God." in prompt
    assert "YHWH" in prompt
    assert "Elohim" in prompt
    assert "Yeshua" in prompt
    assert "purposefully changed" in prompt
    assert "never silently replace God, Lord," not in prompt
    assert "Use familiar English Christian terminology" not in prompt
