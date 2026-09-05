from unittest.mock import AsyncMock, patch

import pytest

from app.api.learning_plan import (
    FAMILY_INVESTIGATION_SLOTS,
    LessonSuggestion,
    _family_investigation_suggestion_for_slot,
    _family_investigation_suggestions,
)


def suggestion(**updates) -> LessonSuggestion:
    values = {
        "id": "skill-1", "title": "Compare ratios", "track": "APPLIED_MATHEMATICS",
        "description": "Use ratios in a new example.", "emoji": "\U0001f4d0", "priority": 1.0,
        "source": "zpd", "concept_id": "ratio-concept", "sequence_policy": "HARD",
        "sequence_state": "READY", "sequence_target_id": "ratio-concept",
        "prerequisite_readiness": 1.0, "delivery_mode": "INDIVIDUAL_SKILL",
    }
    values.update(updates)
    return LessonSuggestion(**values)


def _queue_row(position: int, topic: str, track: str) -> dict:
    return {"id": f"queue-{position}", "position": position, "canonical_topic": topic, "track": track}


@pytest.mark.asyncio
async def test_slot_with_no_completed_items_returns_position_zero_as_current():
    with (
        patch("app.api.learning_plan.family_investigation_queue_store.get_current",
              new=AsyncMock(return_value=_queue_row(0, "Sourdough", "CREATION_SCIENCE"))),
        patch("app.api.learning_plan._shared_investigation_completed", new=AsyncMock(return_value=False)),
    ):
        result = await _family_investigation_suggestion_for_slot("household-1", "science", [suggestion()], "7")
    assert result is not None
    assert result.canonical_topic == "Sourdough"


@pytest.mark.asyncio
async def test_completed_current_item_advances_to_the_next_position():
    # Simulate the queue: position 0 is complete, position 1 is not.
    calls = {"get_current": 0}

    async def fake_get_current(household_id, slot):
        calls["get_current"] += 1
        return _queue_row(0, "Sourdough", "CREATION_SCIENCE") if calls["get_current"] == 1 else _queue_row(1, "Next Unit", "CREATION_SCIENCE")

    mark_completed = AsyncMock()
    with (
        patch("app.api.learning_plan.family_investigation_queue_store.get_current", new=fake_get_current),
        patch("app.api.learning_plan.family_investigation_queue_store.mark_completed", new=mark_completed),
        patch("app.api.learning_plan._shared_investigation_completed", new=AsyncMock(side_effect=[True, False])),
    ):
        result = await _family_investigation_suggestion_for_slot("household-1", "science", [suggestion()], "7")

    assert result is not None
    assert result.canonical_topic == "Next Unit"
    mark_completed.assert_awaited_once()


@pytest.mark.asyncio
async def test_empty_queue_returns_no_suggestion_not_an_error():
    with patch("app.api.learning_plan.family_investigation_queue_store.get_current", new=AsyncMock(return_value=None)):
        result = await _family_investigation_suggestion_for_slot("household-1", "history", [suggestion()], "7")
    assert result is None


@pytest.mark.asyncio
async def test_completion_check_failure_leaves_the_current_item_active():
    with (
        patch("app.api.learning_plan.family_investigation_queue_store.get_current",
              new=AsyncMock(return_value=_queue_row(0, "Sourdough", "CREATION_SCIENCE"))),
        patch("app.api.learning_plan._shared_investigation_completed", new=AsyncMock(side_effect=RuntimeError("db hiccup"))),
    ):
        result = await _family_investigation_suggestion_for_slot("household-1", "science", [suggestion()], "7")
    assert result is not None
    assert result.canonical_topic == "Sourdough"


@pytest.mark.asyncio
async def test_both_slots_present_and_independent_of_each_others_completion():
    assert FAMILY_INVESTIGATION_SLOTS == ("science", "history")

    async def fake_get_current(household_id, slot):
        if slot == "science":
            return _queue_row(0, "Sourdough", "CREATION_SCIENCE")
        return _queue_row(0, "Poison Squad", "TRUTH_HISTORY")

    with (
        patch("app.api.learning_plan.family_investigation_queue_store.get_current", new=fake_get_current),
        patch("app.api.learning_plan._shared_investigation_completed", new=AsyncMock(return_value=False)),
    ):
        results = await _family_investigation_suggestions("household-1", [suggestion()], "7")

    assert len(results) == 2
    topics = {item.canonical_topic for item in results}
    assert topics == {"Sourdough", "Poison Squad"}
    tracks = {item.track for item in results}
    assert tracks == {"CREATION_SCIENCE", "TRUTH_HISTORY"}
