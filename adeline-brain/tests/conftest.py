"""Pytest configuration and fixtures for adeline-brain tests."""
import os
import sys
from unittest.mock import MagicMock, AsyncMock

# Use in-memory storage for the slowapi rate limiter (limits library supports memory://).
# Must be set before app.main is imported (which reads REDIS_URL at module level to
# initialize the Limiter). We mock app.connections.redis_client separately so redis-py
# never tries to connect with this URL.
os.environ.setdefault("REDIS_URL", "memory://")

# Mock pgvector_client before importing any modules that use it
sys.modules["pgvector"] = MagicMock()
sys.modules["pgvector.sqlalchemy"] = MagicMock()

# Mock the hippocampus module early
mock_hippocampus = MagicMock()
mock_hippocampus.similarity_search = AsyncMock()
mock_hippocampus.upsert_document = AsyncMock()
mock_hippocampus.count_documents = AsyncMock()

sys.modules["app.connections.pgvector_client"] = MagicMock()
sys.modules["app.connections.pgvector_client"].hippocampus = mock_hippocampus

# Mock redis_client before app.main imports it. This prevents redis-py from receiving
# the memory:// URL (which it rejects) and avoids real network connections in tests.
mock_redis = MagicMock()
mock_redis.ping = AsyncMock(return_value=True)
mock_redis.get = AsyncMock(return_value=None)
mock_redis.set = AsyncMock(return_value=True)
mock_redis_module = MagicMock()
mock_redis_module.redis_client = mock_redis
mock_redis_module.ping = AsyncMock(return_value=True)
sys.modules["app.connections.redis_client"] = mock_redis_module
