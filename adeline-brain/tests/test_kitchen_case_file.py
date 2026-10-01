"""Forensic science must open as a current family canonical without an LLM."""
from app.agents.adapter import apply_safety_filter
from app.api.experience_builder import _ready_draft_should_rebuild
from app.connections.canonical_store import content_revision_of, repository_copy_supersedes
from app.curriculum.builtin_canonicals import builtin_canonical
from app.curriculum.family_style import is_current_family_canonical
from app.curriculum.kitchen_case_file import CONTENT_REVISION, TOPIC, TRACK, _slug
from app.jobs.canonical_seeding import canonical_seed_for


def test_kitchen_case_is_a_servable_builtin():
    slug = _slug(TOPIC, TRACK)
    record = builtin_canonical(slug)
    assert record is not None
    assert record["topic"] == TOPIC
    assert record["track"] == TRACK
    assert record["title"] == "Forensic Science"
    assert record["pending_approval"] is False
    assert is_current_family_canonical(record["blocks"])
    assert len(record["blocks"]) == 20
    assert builtin_canonical("not-a-real-slug") is None


def test_catalog_seed_resolves_the_same_topic():
    seed = canonical_seed_for(TOPIC, TRACK)
    assert seed is not None
    assert seed.topic == TOPIC
    assert seed.quality_approved
    assert seed.content_revision == CONTENT_REVISION
    assert canonical_seed_for("Kitchen Case File", TRACK) is seed
    assert canonical_seed_for("Forensic Science", TRACK) is seed


def test_unit_teaches_the_real_jobs_and_is_not_stripped_for_a_child():
    record = builtin_canonical(_slug(TOPIC, TRACK))
    text = "\n".join(block["content"].lower() for block in record["blocks"])
    for needle in (
        "bloodstain",
        "forensic pathologist",
        "autopsy",
        "blow flies",
        "brandon mayfield",
        "colin pitchfork",
        "manner",
        "homicide",
    ):
        assert needle in text, needle
    assert "cut apple" not in text
    assert "no real victims" not in text
    for block in record["blocks"]:
        assert block["metadata"]["parent_directed"] is True
        delivered = apply_safety_filter(
            block["content"], block["block_type"], 5, parent_directed=True,
        )
        assert "parent's review" not in delivered
        assert delivered == block["content"]


def test_stale_cached_copy_loses_to_the_revised_unit():
    record = builtin_canonical(_slug(TOPIC, TRACK))
    stale = {"blocks": [{"metadata": {}}]}
    assert repository_copy_supersedes(stale, record) is True
    assert repository_copy_supersedes(record, record) is False
    assert content_revision_of(record) == CONTENT_REVISION
    slug = record["topic_slug"]
    saved_old = {
        "title": "The Kitchen Case File",
        "track": TRACK,
        "canonical_slug": slug,
        "metadata": {"topic": TOPIC},
        "blocks": [
            {"block_type": "TEXT", "content": "A household mystery with the death work removed."},
            {"block_type": "TEXT", "content": "Colored water, not blood."},
            {"block_type": "LAB_MISSION", "content": "Photograph a cut apple."},
        ],
    }
    assert _ready_draft_should_rebuild(saved_old, slug) is True
    assert _ready_draft_should_rebuild(
        {
            "title": record["title"],
            "track": TRACK,
            "canonical_slug": slug,
            "metadata": {"topic": TOPIC},
            "blocks": record["blocks"],
        },
        slug,
    ) is False
