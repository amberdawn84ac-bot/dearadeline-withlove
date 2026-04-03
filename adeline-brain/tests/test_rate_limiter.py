import pytest
from app.utils.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_token_bucket_allows_requests_within_limit():
    """Token bucket allows requests up to max_tokens."""
    bucket = TokenBucket(max_tokens=5, refill_rate=1.0)

    # Should allow 5 requests
    for i in range(5):
        assert await bucket.acquire() == True

    # 6th request should fail
    assert await bucket.acquire() == False


@pytest.mark.asyncio
async def test_token_bucket_refills_over_time():
    """Tokens refill at specified rate."""
    import asyncio

    bucket = TokenBucket(max_tokens=2, refill_rate=1.0)

    # Use both tokens
    await bucket.acquire()
    await bucket.acquire()
    assert await bucket.acquire() == False

    # Wait 1.1 seconds (refill_rate=1 token/sec)
    await asyncio.sleep(1.1)

    # Should have 1 token available
    assert await bucket.acquire() == True
