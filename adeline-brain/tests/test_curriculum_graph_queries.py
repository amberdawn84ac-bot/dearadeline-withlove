from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connections.curriculum_graph import CurriculumGraph
from app.api.learning_plan import GradeLevelStandard, _standard_suggestion


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, traceback):
        return False


@pytest.mark.asyncio
async def test_grade_standards_types_nullable_subject_limit_for_postgres():
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    session = AsyncMock()
    session.execute.return_value = result

    with patch(
        "app.connections.curriculum_graph._get_session_factory",
        return_value=lambda: _SessionContext(session),
    ):
        rows = await CurriculumGraph().get_grade_standards(
            "student-1", 9, limit=500, per_subject_limit=None,
        )

    query, params = session.execute.await_args.args
    assert "CAST(:per_subject_limit AS INTEGER)" in str(query)
    assert params["per_subject_limit"] is None
    assert rows == []


def test_unfinished_standard_becomes_a_real_mission_target():
    standard = GradeLevelStandard(
        standard_id="9.ELA.1",
        subject="English Language Arts",
        grade=9,
        description="Evaluate how evidence supports an argument.",
        mastered=False,
        priority=1,
        track="ENGLISH_LITERATURE",
        lesson_hook="Investigate a claim affecting your community",
    )

    suggestion = _standard_suggestion(standard)

    assert suggestion.id == "standard-9.ELA.1"
    assert suggestion.standard_code == "9.ELA.1"
    assert suggestion.title == (
        "Investigate a claim affecting your community — "
        "Evaluate how evidence supports an argument"
    )
    assert suggestion.track == "ENGLISH_LITERATURE"


def test_shared_hook_still_produces_distinct_canonical_topics():
    first = GradeLevelStandard(
        standard_id="9.ELA.1", subject="English Language Arts", grade=9,
        description="Students will evaluate evidence supporting an argument.",
        mastered=False, priority=1, track="ENGLISH_LITERATURE",
        lesson_hook="What does this text say?",
    )
    second = first.model_copy(update={
        "standard_id": "9.ELA.2",
        "description": "Students will evaluate a speaker's purpose and perspective.",
    })

    assert _standard_suggestion(first).title != _standard_suggestion(second).title


def test_standard_topic_is_concise_and_uses_an_action_verb():
    standard = GradeLevelStandard(
        standard_id="BIBLIC_G9_D.9.1", subject="Biblical Worldview & Ethics", grade=9,
        description=(
            "The student outlines and defends the major loci of Christian systematic "
            "theology — Scripture, God, humanity, salvation, Church, and eschatology."
        ),
        mastered=False, priority=1, track="DISCIPLESHIP",
        lesson_hook="How does Scripture speak to this?",
    )

    title = _standard_suggestion(standard).title

    assert " — Outline and defend " in title
    assert title.endswith("…")
    assert len(title) < 110
