"""Regression tests for the web-search path that replaced Tavily with DDG."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools import researcher
from app.utils.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_ddg_concurrency_limiter_exists():
    """The free search backend keeps a small module-level concurrency cap."""
    assert isinstance(researcher._ddg_semaphore, asyncio.Semaphore)
    assert researcher._ddg_semaphore._value == 3


@pytest.mark.asyncio
async def test_search_archive_rejects_unknown_archive():
    result = await researcher.search_archive_async("test query", "NOT_A_SOURCE")
    assert result == []


@pytest.mark.asyncio
async def test_search_archive_normalizes_ddg_results():
    ddgs = MagicMock()
    ddgs.text.return_value = [{
        "title": "Archive result",
        "href": "https://example.com/document",
        "body": "Primary-source excerpt",
    }]

    with patch("duckduckgo_search.DDGS", return_value=ddgs):
        result = await researcher.search_archive_async("test query", "NARA")

    assert result == [{
        "title": "Archive result",
        "url": "https://example.com/document",
        "archive": "NARA",
        "snippet": "Primary-source excerpt",
    }]
    ddgs.text.assert_called_once_with(
        "test query site:catalog.archives.gov",
        max_results=researcher.DDG_MAX_RESULTS,
    )


@pytest.mark.asyncio
async def test_search_archive_retries_transient_failures():
    ddgs = MagicMock()
    ddgs.text.side_effect = RuntimeError("temporary search failure")

    with patch("duckduckgo_search.DDGS", return_value=ddgs), patch.object(
        researcher.asyncio, "sleep", new=AsyncMock()
    ) as sleep:
        result = await researcher.search_archive_async("test query", "NARA")

    assert result == []
    assert ddgs.text.call_count == 3
    assert sleep.await_count == 2
    sleep.assert_any_await(1)
    sleep.assert_any_await(2)


@pytest.mark.asyncio
async def test_search_all_archives_uses_default_science_sources():
    async def fake_search(query, archive_name, domains_map):
        return [{"title": archive_name, "url": f"https://{archive_name}", "archive": archive_name}]

    with patch.object(researcher, "search_archive_async", side_effect=fake_search) as search:
        result = await researcher.search_all_archives_parallel("test query")

    assert search.await_count == len(researcher.SCIENCE_DOMAINS)
    assert {row["archive"] for row in result} == set(researcher.SCIENCE_DOMAINS)


@pytest.mark.asyncio
async def test_search_all_archives_uses_track_specific_sources():
    async def fake_search(query, archive_name, domains_map):
        assert domains_map is researcher.PRIMARY_SOURCE_DOMAINS
        return []

    with patch.object(researcher, "search_archive_async", side_effect=fake_search) as search:
        await researcher.search_all_archives_parallel("test query", "TRUTH_HISTORY")

    assert search.await_count == len(researcher.PRIMARY_SOURCE_DOMAINS)


@pytest.mark.asyncio
async def test_search_all_archives_deduplicates_urls():
    duplicate = {
        "title": "Same document",
        "url": "https://example.com/document",
        "archive": "source",
    }

    with patch.object(
        researcher,
        "search_archive_async",
        new=AsyncMock(return_value=[duplicate]),
    ):
        result = await researcher.search_all_archives_parallel("test query")

    assert result == [duplicate]


@pytest.mark.asyncio
async def test_search_with_fallback_reports_empty_results():
    with patch.object(
        researcher,
        "search_all_archives_parallel",
        new=AsyncMock(return_value=[]),
    ):
        results, fallback = await researcher.search_with_fallback("test query")

    assert results == []
    assert fallback is True


@pytest.mark.asyncio
async def test_token_bucket_depletes_and_refills():
    with patch("app.utils.rate_limiter.time.monotonic", return_value=100.0) as clock:
        limiter = TokenBucket(max_tokens=1, refill_rate=0.5)
        assert await limiter.acquire(tokens=1.0)
        assert not await limiter.acquire(tokens=1.0)

        clock.return_value = 102.1
        assert await limiter.acquire(tokens=1.0)
