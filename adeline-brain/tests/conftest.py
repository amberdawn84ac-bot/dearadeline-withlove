"""Pytest configuration and fixtures for adeline-brain tests."""
import sys
from unittest.mock import MagicMock, AsyncMock

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
