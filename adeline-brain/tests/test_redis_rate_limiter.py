"""Verify rate limiter uses Redis storage (not memory://)."""
import os
import pytest
from app.main import limiter


@pytest.mark.skipif(
    os.environ.get("REDIS_URL", "memory://").startswith("memory://"),
    reason="Skipped in test environment where REDIS_URL=memory:// (deployment guard only)",
)
def test_rate_limiter_uses_redis_storage():
    """The rate limiter storage_uri must NOT be memory:// in production."""
    storage_uri = str(limiter._storage_uri)
    assert storage_uri != "memory://", (
        "Rate limiter is using in-memory storage — "
        "this breaks across Railway replicas. Set REDIS_URL."
    )
    assert "redis" in storage_uri.lower(), (
        f"Expected Redis storage URI, got: {storage_uri}"
    )
