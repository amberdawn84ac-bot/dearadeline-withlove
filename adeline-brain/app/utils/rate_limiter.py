"""Token bucket rate limiter for API calls."""
import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Token bucket rate limiter (sliding window).

    Implements the token bucket algorithm for rate limiting API calls.
    Tokens refill at a constant rate (tokens per second) up to max_tokens.
    """
    max_tokens: float
    refill_rate: float  # Tokens per second
    _tokens: float = field(default=None)
    _last_refill: float = field(default=None)
    _lock: asyncio.Lock = field(default=None)

    def __post_init__(self):
        """Initialize tokens and lock."""
        if self._tokens is None:
            self._tokens = self.max_tokens
        if self._last_refill is None:
            self._last_refill = time.monotonic()
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens from the bucket.

        Returns True if successful, False if insufficient tokens.

        Args:
            tokens: Number of tokens to acquire (default: 1.0)

        Returns:
            bool: True if tokens were acquired, False otherwise
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill

            # Refill tokens based on elapsed time
            self._tokens = min(
                self.max_tokens,
                self._tokens + (elapsed * self.refill_rate)
            )
            self._last_refill = now

            # Try to acquire requested tokens
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def wait_for_acquire(self, tokens: float = 1.0) -> None:
        """
        Wait until tokens are available, then acquire them.

        Blocks asynchronously until the requested tokens become available.

        Args:
            tokens: Number of tokens to acquire (default: 1.0)
        """
        while not await self.acquire(tokens):
            await asyncio.sleep(0.1)
