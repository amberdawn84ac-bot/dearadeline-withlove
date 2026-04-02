import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.connections.pgvector_client import HippocampusDocument


def test_hippocampus_document_has_source_type():
    """HippocampusDocument model must have a source_type column."""
    columns = {c.name for c in HippocampusDocument.__table__.columns}
    assert "source_type" in columns, "HippocampusDocument missing source_type column"


def test_hippocampus_document_source_type_default():
    """source_type should default to PRIMARY_SOURCE for backward compat."""
    doc = HippocampusDocument(
        source_title="Test",
        source_url="https://example.com",
        track="TRUTH_HISTORY",
        chunk="test chunk",
        embedding=[0.1] * 1536,
    )
    assert doc.source_type == "PRIMARY_SOURCE"
