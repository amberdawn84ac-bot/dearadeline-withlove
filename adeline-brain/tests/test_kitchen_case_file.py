"""The Kitchen Case File must open as a current family canonical without an LLM."""
from app.curriculum.builtin_canonicals import builtin_canonical
from app.curriculum.family_style import is_current_family_canonical
from app.curriculum.kitchen_case_file import TOPIC, TRACK, _slug
from app.jobs.canonical_seeding import canonical_seed_for


def test_kitchen_case_is_a_servable_builtin():
    slug = _slug(TOPIC, TRACK)
    record = builtin_canonical(slug)
    assert record is not None
    assert record["topic"] == TOPIC
    assert record["track"] == TRACK
    assert record["pending_approval"] is False
    assert is_current_family_canonical(record["blocks"])
    assert builtin_canonical("not-a-real-slug") is None


def test_catalog_seed_resolves_the_same_topic():
    seed = canonical_seed_for(TOPIC, TRACK)
    assert seed is not None
    assert seed.topic == TOPIC
    assert seed.quality_approved
    assert canonical_seed_for("Kitchen Case File", TRACK) is seed
