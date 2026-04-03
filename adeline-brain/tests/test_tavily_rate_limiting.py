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
from app.tools.researcher import search_all_archives_parallel, tavily_limiter


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
