"""Tests for retry logic in seed_declassified_documents.py."""
import pytest
from unittest.mock import AsyncMock, patch
from app.scripts.seed_declassified_documents import _retry_search


@pytest.mark.asyncio
async def test_retry_search_succeeds_on_second_attempt():
    """Retry logic succeeds after transient failure."""
    call_count = [0]

    async def flaky_search(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ConnectionError("Network error")
        return [{"title": "Success"}]

    result = await _retry_search(
        query="test",
        archive="NARA",
        max_retries=3,
        search_fn=flaky_search,
    )

    assert len(result) == 1
    assert result[0]["title"] == "Success"
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_retry_search_gives_up_after_max_retries():
    """Retry logic gives up after max_retries exceeded."""
    call_count = [0]

    async def always_fails(*args, **kwargs):
        call_count[0] += 1
        raise ConnectionError("Network error")

    with pytest.raises(ConnectionError):
        await _retry_search(
            query="test",
            archive="NARA",
            max_retries=3,
            search_fn=always_fails,
        )

    # Should have tried 3 times (1 initial + 2 retries)
    assert call_count[0] == 3


@pytest.mark.asyncio
async def test_retry_search_succeeds_on_first_try():
    """Retry logic succeeds on first attempt."""
    call_count = [0]

    async def successful_search(*args, **kwargs):
        call_count[0] += 1
        return [{"title": "Document 1"}, {"title": "Document 2"}]

    result = await _retry_search(
        query="test",
        archive="NARA",
        max_retries=3,
        search_fn=successful_search,
    )

    assert len(result) == 2
    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_retry_search_handles_timeout_errors():
    """Retry logic handles TimeoutError as transient."""
    call_count = [0]

    async def timeout_then_success(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise TimeoutError("Request timeout")
        return [{"title": "Success"}]

    result = await _retry_search(
        query="test",
        archive="CIA_FOIA",
        max_retries=3,
        search_fn=timeout_then_success,
    )

    assert len(result) == 1
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_retry_search_with_custom_initial_delay():
    """Retry logic respects custom initial_delay parameter."""
    call_count = [0]

    async def flaky_search(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ConnectionError("Network error")
        return [{"title": "Success"}]

    with patch("asyncio.sleep") as mock_sleep:
        result = await _retry_search(
            query="test",
            archive="NARA",
            max_retries=2,
            search_fn=flaky_search,
            initial_delay=1.0,
        )

        assert len(result) == 1
        # Verify sleep was called with a delay close to initial_delay (with jitter)
        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args[0][0]
        # Should be roughly 1.0 second (±10%)
        assert 0.85 < sleep_arg < 1.15


@pytest.mark.asyncio
async def test_retry_search_non_transient_error_not_retried():
    """Retry logic does NOT retry non-transient errors."""
    call_count = [0]

    async def value_error_search(*args, **kwargs):
        call_count[0] += 1
        raise ValueError("Invalid query")

    with pytest.raises(ValueError):
        await _retry_search(
            query="test",
            archive="NARA",
            max_retries=3,
            search_fn=value_error_search,
        )

    # Should only try once, no retries for ValueError
    assert call_count[0] == 1
