from app.connections.canonical_store import canonical_slug
from app.curriculum.builtin_canonicals import builtin_canonical


def test_children_who_changed_history_is_repository_canonical():
    slug = canonical_slug("Children Who Changed History", "JUSTICE_CHANGEMAKING")
    lesson = builtin_canonical(slug)
    assert lesson is not None
    assert lesson["family_style"] is True
    assert lesson["pending_approval"] is False
    assert len(lesson["blocks"]) >= 7
    assert any(block["block_type"] == "LAB_MISSION" for block in lesson["blocks"])
