from app.connections.canonical_store import canonical_slug
from app.curriculum.builtin_canonicals import builtin_canonical


def test_repository_does_not_bypass_the_approved_canonical_store():
    slug = canonical_slug("Children Who Changed History", "JUSTICE_CHANGEMAKING")
    assert builtin_canonical(slug) is None
