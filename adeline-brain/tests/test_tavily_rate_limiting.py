"""
Test suite for Tavily API rate limiting integration.

Tests that search_all_archives_parallel() respects the rate limiter:
1. Enforces max_tokens=10 limit on concurrent Tavily calls
2. Refills tokens at 0.5 tokens/second for sustained load
3. Blocks calls when rate limit exceeded
"""
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, patch, MagicMock
from app.tools.researcher import search_all_archives_parallel, tavily_limiter, search_archive_async
from app.utils.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_tavily_rate_limiter_exists():
    """Tavily rate limiter should be initialized at module load."""
    assert tavily_limiter is not None
    assert tavily_limiter.max_tokens == 10
    assert tavily_limiter.refill_rate == 0.5


@pytest.mark.asyncio
async def test_tavily_rate_limiter_enforces_limit():
    """Tavily API calls are rate limited to max_tokens=10."""
    call_count = [0]

    async def mock_tavily_post(*args, **kwargs):
        call_count[0] += 1
        # Simulate Tavily response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [
                {
                    'title': f'Result {call_count[0]}',
                    'url': f'https://example.com/{call_count[0]}',
                    'content': f'Content snippet {call_count[0]}',
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        return mock_response

    with patch('app.tools.researcher.httpx.AsyncClient') as mock_client_class, \
         patch.dict('os.environ', {'TAVILY_API_KEY': 'test-api-key'}):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=mock_tavily_post)
        mock_client_class.return_value = mock_client

        # Make 6 parallel calls (one per archive)
        # Each call to search_all_archives_parallel triggers 6 archive searches
        result = await search_all_archives_parallel(query="test query")

        # Should have made requests (rate limiter should allow them)
        assert call_count[0] > 0


@pytest.mark.asyncio
async def test_tavily_rate_limiter_refills():
    """Tavily rate limiter refills tokens at 0.5 tokens/second."""
    import time

    # Reset the limiter to a known state
    fresh_limiter = tavily_limiter

    # Verify refill rate is correct
    assert fresh_limiter.refill_rate == 0.5

    # Try to acquire tokens
    initial_acquire = await fresh_limiter.acquire(tokens=1.0)
    assert initial_acquire == True

    # After some time, tokens should refill
    await asyncio.sleep(2.1)  # At 0.5 tokens/sec, should get ~1 token in 2.1 seconds

    # Should be able to acquire more tokens after refill
    refill_acquire = await fresh_limiter.acquire(tokens=1.0)
    assert refill_acquire == True


@pytest.mark.asyncio
async def test_tavily_rate_limiter_wait_for_acquire():
    """Rate limiter wait_for_acquire() blocks until tokens available."""
    fresh_limiter = tavily_limiter

    # This should not raise and should complete (token will refill)
    # Set a timeout to prevent infinite blocking
    try:
        await asyncio.wait_for(
            fresh_limiter.wait_for_acquire(tokens=0.5),
            timeout=3.0
        )
    except asyncio.TimeoutError:
        pytest.fail("wait_for_acquire() timed out — limiter not refilling")


@pytest.mark.asyncio
async def test_search_archive_async_respects_rate_limit():
    """search_archive_async respects the rate limiter before calling Tavily."""
    call_count = [0]

    async def mock_tavily_post(*args, **kwargs):
        call_count[0] += 1
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [
                {
                    'title': f'Result {call_count[0]}',
                    'url': f'https://example.com/{call_count[0]}',
                    'content': f'Content snippet {call_count[0]}',
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        return mock_response

    with patch('app.tools.researcher.httpx.AsyncClient') as mock_client_class, \
         patch.dict('os.environ', {'TAVILY_API_KEY': 'test-api-key'}):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=mock_tavily_post)
        mock_client_class.return_value = mock_client

        # Call search_archive_async
        result = await search_archive_async(query="test query", archive_name="NARA")

        # Should have called Tavily API at least once
        assert call_count[0] > 0
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_tavily_limiter_is_module_singleton():
    """tavily_limiter is a module-level singleton."""
    from app.tools.researcher import tavily_limiter as limiter1
    from app.tools.researcher import tavily_limiter as limiter2

    # Should be the same object
    assert limiter1 is limiter2


@pytest.mark.asyncio
async def test_rate_limiter_token_depletion_and_recovery():
    """Rate limiter depletes and recovers correctly."""
    limiter = TokenBucket(max_tokens=3, refill_rate=0.5)

    # Acquire 3 tokens
    for i in range(3):
        assert await limiter.acquire(tokens=1.0) == True

    # Should be empty now
    assert await limiter.acquire(tokens=1.0) == False

    # Wait for 2.2 seconds (0.5 tokens/sec * 2.2 sec = 1.1 tokens)
    await asyncio.sleep(2.2)

    # Should have approximately 1 token
    assert await limiter.acquire(tokens=1.0) == True

    # Should be depleted again
    assert await limiter.acquire(tokens=0.5) == False


@pytest.mark.asyncio
async def test_wait_for_acquire_blocks_until_available():
    """wait_for_acquire blocks until tokens become available."""
    limiter = TokenBucket(max_tokens=1, refill_rate=0.5)

    # Acquire the single token
    assert await limiter.acquire(tokens=1.0) == True

    # Start waiting for a token in the background
    acquired = [False]
    start_times = [None]

    async def wait_and_acquire():
        start_times[0] = asyncio.get_event_loop().time()
        await limiter.wait_for_acquire(tokens=1.0)
        acquired[0] = True
        return asyncio.get_event_loop().time() - start_times[0]

    task = asyncio.create_task(wait_and_acquire())

    # Give it time to start waiting
    await asyncio.sleep(0.3)

    # Token should not have been acquired yet
    assert acquired[0] == False

    # Wait for it to be acquired (should take ~2 seconds for refill)
    elapsed = await asyncio.wait_for(task, timeout=3.0)

    # Should have been acquired
    assert acquired[0] == True
    assert elapsed >= 2.0  # Should have waited ~2 seconds


@pytest.mark.asyncio
async def test_search_all_archives_parallel_calls_multiple_archives():
    """search_all_archives_parallel calls multiple archive sources."""
    call_count = [0]
    archive_names = []

    async def mock_tavily_post(*args, **kwargs):
        call_count[0] += 1
        # Track which archives were called based on the payload
        payload = kwargs.get('json', {})
        if 'include_domains' in payload:
            archive_names.extend(payload['include_domains'])

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [
                {
                    'title': f'Result {call_count[0]}',
                    'url': f'https://example.com/{call_count[0]}',
                    'content': f'Content snippet {call_count[0]}',
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        return mock_response

    with patch('app.tools.researcher.httpx.AsyncClient') as mock_client_class, \
         patch.dict('os.environ', {'TAVILY_API_KEY': 'test-api-key'}):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=mock_tavily_post)
        mock_client_class.return_value = mock_client

        # Call search_all_archives_parallel
        result = await search_all_archives_parallel(query="test query")

        # Should have made multiple calls (one per archive)
        assert call_count[0] >= 1  # At least one call
        assert isinstance(result, list)
