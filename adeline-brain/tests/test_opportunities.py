import pytest

from app.api.opportunities import _cache_key, _fallbacks, refresh_opportunity_index
from app.jobs import seed_scheduler


def test_opportunity_cache_key_is_stable():
    assert _cache_key("Oklahoma", "Oklahoma", 8) == "oklahoma|oklahoma|8"


def test_fallbacks_hide_paid_work_from_younger_grades():
    young = _fallbacks("Oklahoma", 6)
    assert young
    assert all(item["category"] != "PAID_WORK" for item in young)
    assert all(item["verification_status"] == "DIRECTORY" for item in young)


@pytest.mark.asyncio
async def test_weekly_refresh_swallows_search_failures(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("search down")

    monkeypatch.setattr("app.api.opportunities._live_search", boom)
    stored = await refresh_opportunity_index()
    assert stored == 0


def test_scheduler_registers_weekly_opportunity_scrape():
    source = open(seed_scheduler.__file__, encoding="utf-8").read()
    assert "refresh_opportunity_index" in source
    assert "refresh_opportunities_weekly" in source
    assert "Sunday" in source or "sun" in source
