from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.api.learning_plan import LessonSuggestion, _family_investigation_suggestion


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


@pytest.mark.asyncio
async def test_pinned_override_wins_over_the_algorithmic_rotation():
    catalog = (("saved-canonical", "Railroads and Power", "TRUTH_HISTORY", "Compare the records."),)
    plan_date = date(2026, 9, 7)  # ISO week 37, 2026
    pin = {"canonical_topic": "Kitchen Chemistry: The Science of Sourdough", "track": "CREATION_SCIENCE"}
    with patch(
        "app.api.learning_plan.family_investigation_override_store.get",
        new=AsyncMock(return_value=pin),
    ):
        result = await _family_investigation_suggestion(
            "household-1", plan_date, [suggestion()], "7", catalog,
        )
    assert result is not None
    assert result.canonical_topic == "Kitchen Chemistry: The Science of Sourdough"
    assert result.track == "CREATION_SCIENCE"


@pytest.mark.asyncio
async def test_no_override_falls_through_to_the_unchanged_rotation():
    catalog = (("saved-canonical", "Railroads and Power", "TRUTH_HISTORY", "Compare the records."),)
    plan_date = date(2026, 9, 7)
    with patch(
        "app.api.learning_plan.family_investigation_override_store.get",
        new=AsyncMock(return_value=None),
    ):
        result = await _family_investigation_suggestion(
            "household-1", plan_date, [suggestion()], "7", catalog,
        )
    assert result is not None
    assert result.canonical_topic == "Railroads and Power"
    assert result.title == "Railroads and Power"


@pytest.mark.asyncio
async def test_override_only_applies_to_its_pinned_iso_week():
    catalog = (("saved-canonical", "Railroads and Power", "TRUTH_HISTORY", "Compare the records."),)
    pinned_week_date = date(2026, 9, 7)   # ISO week 37
    other_week_date = date(2026, 9, 14)   # ISO week 38

    async def fake_get(household_id, iso_year, iso_week):
        if iso_week == 37:
            return {"canonical_topic": "Kitchen Chemistry: The Science of Sourdough", "track": "CREATION_SCIENCE"}
        return None

    with patch("app.api.learning_plan.family_investigation_override_store.get", new=AsyncMock(side_effect=fake_get)):
        pinned = await _family_investigation_suggestion("household-1", pinned_week_date, [suggestion()], "7", catalog)
        other = await _family_investigation_suggestion("household-1", other_week_date, [suggestion()], "7", catalog)

    assert pinned.canonical_topic == "Kitchen Chemistry: The Science of Sourdough"
    assert other.canonical_topic == "Railroads and Power"


@pytest.mark.asyncio
async def test_override_lookup_failure_falls_back_to_rotation_instead_of_erroring():
    catalog = (("saved-canonical", "Railroads and Power", "TRUTH_HISTORY", "Compare the records."),)
    with patch(
        "app.api.learning_plan.family_investigation_override_store.get",
        new=AsyncMock(side_effect=RuntimeError("db hiccup")),
    ):
        result = await _family_investigation_suggestion(
            "household-1", date(2026, 9, 7), [suggestion()], "7", catalog,
        )
    assert result is not None
    assert result.canonical_topic == "Railroads and Power"
