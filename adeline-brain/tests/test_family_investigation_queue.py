"""Universal family queue replaces independent science/history slots."""
from unittest.mock import AsyncMock, patch
import pytest
from app.api.learning_plan import _family_investigation_suggestions, _upcoming_family_investigations, FAMILY_INVESTIGATION_SLOTS


@pytest.mark.asyncio
async def test_empty_queue_has_no_family_investigation():
    with patch('app.api.learning_plan.family_unit_store.current',new=AsyncMock(return_value=None)):
        assert await _family_investigation_suggestions('household',[],'7')==[]


@pytest.mark.asyncio
async def test_only_one_family_slot_exists():
    assert FAMILY_INVESTIGATION_SLOTS==('family',)


@pytest.mark.asyncio
async def test_upcoming_units_share_one_order_across_subjects():
    with patch('app.api.learning_plan.family_unit_store.upcoming',new=AsyncMock(return_value=[
        {'title':'Weather','track':'CREATION_SCIENCE','position':1},
        {'title':'Railroads','track':'TRUTH_HISTORY','position':2},
    ])):
        result=await _upcoming_family_investigations('household')
    assert [item.slot for item in result]==['family','family']
    assert [item.canonical_topic for item in result]==['Weather','Railroads']
