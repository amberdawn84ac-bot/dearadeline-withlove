from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.connections.daily_plan_store import DailyPlanStore


@pytest.mark.asyncio
async def test_household_plan_reuses_explicit_family_investigation():
    family = {
        "id": "family-week-1",
        "title": "Railroads and Power",
        "delivery_mode": "FAMILY_INVESTIGATION",
    }
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"planJson": {"family_investigation": None}},
        {"planJson": {"family_investigation": family}},
    ]
    with patch(
        "app.connections.daily_plan_store.get_db_conn",
        new=AsyncMock(return_value=conn),
    ):
        result = await DailyPlanStore().get_household_family_investigation(
            "parent-1", date(2026, 8, 26),
        )

    assert result == family
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_completion_clears_the_matching_lane_without_deleting_the_plan():
    conn = AsyncMock()
    conn.fetchrow.return_value = {"planJson": {
        "suggestions": [], "individual_skills": [], "family_investigation": None,
    }}
    with patch(
        "app.connections.daily_plan_store.get_db_conn",
        new=AsyncMock(return_value=conn),
    ):
        result = await DailyPlanStore().remove_suggestion(
            "student-1", date(2026, 8, 26), "family-week-1",
        )

    query = conn.fetchrow.await_args.args[0]
    assert "{suggestions}" in query
    assert "{individual_skills}" in query
    assert "{family_investigation}" in query
    assert result == {
        "suggestions": [], "individual_skills": [], "family_investigation": None,
    }
