"""Rejected forensic teaching content cannot be served or reseeded."""
from app.connections.canonical_store import canonical_slug
from app.curriculum.builtin_canonicals import builtin_canonical, unit_experiences
from app.curriculum.kitchen_case_file import TOPIC, TRACK
from app.jobs.canonical_seeding import canonical_seeding_enabled


def test_old_forensic_lesson_is_not_servable():
    assert builtin_canonical(canonical_slug(TOPIC,TRACK)) is None
    assert builtin_canonical('not-a-real-slug') is None


def test_old_forensic_topic_is_not_expanded_into_hardcoded_lessons():
    assert unit_experiences(TOPIC,TRACK)==[{'canonical_topic':TOPIC,'track':TRACK}]


def test_environment_cannot_restore_old_pre_authored_content(monkeypatch):
    monkeypatch.setenv('CANONICAL_SEEDING_ENABLED','true')
    assert canonical_seeding_enabled() is False
