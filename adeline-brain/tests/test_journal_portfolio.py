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
    connection.close.assert_awaited_once()
