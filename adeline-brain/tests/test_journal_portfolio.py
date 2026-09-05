from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.api.journal import get_portfolio_items


@pytest.mark.asyncio
async def test_portfolio_decodes_saved_reflection_and_artifact():
    connection = AsyncMock()
    connection.fetch.return_value = [{
        "lesson_id": "lesson-1",
        "track": "ENGLISH_LITERATURE",
        "title": "The Art of Persuasion",
        "sealed_at": datetime(2026, 8, 24, tzinfo=timezone.utc),
        "plan_item_id": None,
        "sources_json": (
            '[{"type":"learner_reflection","content":"Words should serve truth."},'
            '{"type":"artifact","url":"portfolio://investigation/lesson-1",'
            '"title":"Persuasive letter","author":"Letter and annotated evidence"},'
            '{"type":"artifact","url":"portfolio://investigation/lesson-1"}]'
        ),
    }]

    with patch("app.config.get_db_conn", new=AsyncMock(return_value=connection)):
        response = await get_portfolio_items("student-1", _user_id="student-1")

    assert len(response.items) == 1
    assert response.items[0].reflection == "Words should serve truth."
    assert response.items[0].artifact_description == "Letter and annotated evidence"
    assert response.items[0].artifact_refs == ["portfolio://investigation/lesson-1"]
    assert response.items[0].plan_item_id is None
    connection.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_portfolio_item_carries_the_space_it_came_from():
    connection = AsyncMock()
    connection.fetch.return_value = [{
        "lesson_id": "lesson-1",
        "track": "CREATION_SCIENCE",
        "title": "Kitchen Chemistry: The Science of Sourdough",  # resolved via plan_item_id join
        "sealed_at": datetime(2026, 9, 5, tzinfo=timezone.utc),
        "plan_item_id": "family-abc123-science-0",
        "sources_json": '[{"type":"space_conversation_transcript","lesson_title":"Feeding the starter","concepts":["Wild yeast capture"]}]',
    }]

    with patch("app.config.get_db_conn", new=AsyncMock(return_value=connection)):
        response = await get_portfolio_items("student-1", _user_id="student-1")

    assert response.items[0].plan_item_id == "family-abc123-science-0"
    assert response.items[0].title == "Kitchen Chemistry: The Science of Sourdough"


@pytest.mark.asyncio
async def test_spaces_insights_merges_credited_and_encountered_sorted_by_recency():
    from app.api.parent import get_spaces_insights

    connection = AsyncMock()
    connection.fetchrow.return_value = {"role": "PARENT"}
    connection.fetch.side_effect = [
        [
            {
                "track": "CREATION_SCIENCE",
                "sources_json": (
                    '[{"type":"space_conversation_transcript","lesson_title":"Feeding the starter",'
                    '"concepts":["Wild yeast capture"]}]'
                ),
                "sealed_at": datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
                "student_name": "Ellie",
            },
            {
                "track": "TRUTH_HISTORY",
                "sources_json": '[{"type":"rabbit_hole_conversation","concept":"Regulatory capture"}]',
                "sealed_at": datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc),
                "student_name": "Jack",
            },
        ],
        [
            {
                "track": "CREATION_SCIENCE",
                "conceptName": "Osmosis",
                "encounteredAt": datetime(2026, 9, 5, 11, 0, tzinfo=timezone.utc),
                "student_name": "Ellie",
            },
        ],
    ]

    with (
        patch("app.config.get_db_conn", new=AsyncMock(return_value=connection)),
        patch("app.api.parent.get_current_user_id", return_value="parent-1"),
    ):
        response = await get_spaces_insights(limit=20, authorization="Bearer token")

    assert [item.at for item in response.insights] == sorted((item.at for item in response.insights), reverse=True)
    kinds = {(item.kind, item.student_name) for item in response.insights}
    assert ("credited", "Jack") in kinds
    assert ("credited", "Ellie") in kinds
    assert ("encountered", "Ellie") in kinds
    credited_ellie = next(item for item in response.insights if item.kind == "credited" and item.student_name == "Ellie")
    assert credited_ellie.concept_names == ["Wild yeast capture"]
    assert credited_ellie.context == "Feeding the starter"
    encountered = next(item for item in response.insights if item.kind == "encountered")
    assert encountered.concept_names == ["Osmosis"]
