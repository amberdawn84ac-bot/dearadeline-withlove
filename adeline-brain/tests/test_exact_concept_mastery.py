import pytest

from app.api.journal import SealRequest, _update_card_safe
from app.schemas.api_models import Track


@pytest.mark.asyncio
async def test_quiz_without_exact_concept_never_guesses_a_mastery_target(monkeypatch):
    calls = []

    async def record_call(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        "app.algorithms.bkt_tracker.update_card_after_lesson", record_call
    )
    body = SealRequest(
        lesson_id="lesson-1",
        track=Track.APPLIED_MATHEMATICS,
        quiz_results=[{"correct": True}],
    )
    await _update_card_safe("student-1", body)
    assert calls == []


@pytest.mark.asyncio
async def test_quiz_updates_only_the_exact_planned_concept(monkeypatch):
    calls = []

    async def record_call(**kwargs):
        calls.append(kwargs)
        return .8

    monkeypatch.setattr(
        "app.algorithms.bkt_tracker.update_card_after_lesson", record_call
    )
    body = SealRequest(
        lesson_id="lesson-1",
        track=Track.APPLIED_MATHEMATICS,
        concept_id="am-003",
        concept_name="Fractions in Real Life",
        quiz_results=[{"correct": True}],
    )
    await _update_card_safe("student-1", body)
    assert len(calls) == 1
    assert calls[0]["concept_id"] == "am-003"
