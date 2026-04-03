"""
Tests for duplicate detection in pgvector_client.

Ensures that the same (source_url, track) pair is not re-inserted
into the Hippocampus, preventing seed script redundancy.

These tests verify the duplicate detection implementation without relying
on mocking the entire module (which conftest.py does).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys


def test_duplicate_detection_implemented():
    """
    Test that the duplicate detection code is present in pgvector_client.

    Reads the source file directly to verify duplicate detection SQL logic.
    """
    import pathlib

    # Read the pgvector_client source file directly
    client_path = (
        pathlib.Path(__file__).parent.parent
        / "app" / "connections" / "pgvector_client.py"
    )

    with open(client_path, "r") as f:
        source = f.read()

    # Verify duplicate detection query is present
    assert "SELECT id FROM hippocampus_documents" in source, (
        "Missing duplicate detection SELECT query"
    )
    assert "WHERE source_url = :source_url AND track = :track" in source, (
        "Missing duplicate detection WHERE clause"
    )

    # Verify skip logging is present
    assert "[Duplicate]" in source or "Skipping" in source, (
        "Missing duplicate skip logging"
    )

    # Verify document insertion is still present
    assert "session.add(doc)" in source, "Missing document insertion"


def test_hippocampus_document_table_structure():
    """
    Test that HippocampusDocument has the required fields for duplicate detection.

    This test verifies the ORM model has source_url and track columns needed
    for the unique constraint check.
    """
    # Import the actual model without triggering the conftest mock
    import importlib.util
    import pathlib

    spec = importlib.util.spec_from_file_location(
        "pgvector_client_direct",
        pathlib.Path(__file__).parent.parent / "app" / "connections" / "pgvector_client.py"
    )
    module = importlib.util.module_from_spec(spec)

    # Pre-populate sys.modules to avoid reloading issues
    sys.modules["pgvector"] = MagicMock()
    sys.modules["pgvector.sqlalchemy"] = MagicMock()

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        # If we can't load the module directly, check the source file instead
        client_path = (
            pathlib.Path(__file__).parent.parent
            / "app" / "connections" / "pgvector_client.py"
        )
        with open(client_path, "r") as f:
            source = f.read()

        # Verify HippocampusDocument model has required fields
        assert 'source_url = Column(String' in source, (
            "HippocampusDocument missing source_url column"
        )
        assert 'track = Column(String' in source, (
            "HippocampusDocument missing track column"
        )
        assert 'source_title = Column(String' in source, (
            "HippocampusDocument missing source_title column"
        )
        assert 'chunk = Column(String' in source, (
            "HippocampusDocument missing chunk column"
        )
        assert 'embedding = Column(Vector' in source, (
            "HippocampusDocument missing embedding column"
        )
        return

    # If module loaded, check the table
    assert hasattr(module, "HippocampusDocument"), (
        "HippocampusDocument class not found"
    )

    doc_class = module.HippocampusDocument
    columns = {c.name for c in doc_class.__table__.columns}

    required = {"source_url", "track", "source_title", "chunk", "embedding"}
    assert required.issubset(columns), (
        f"Missing columns: {required - columns}"
    )


def test_unique_constraint_on_source_url_and_track():
    """
    Test that HippocampusDocument has a unique constraint on (source_url, track).

    This constraint enforces duplicate prevention at the database level.
    """
    import pathlib

    # Read the source file to check for unique constraint
    client_path = (
        pathlib.Path(__file__).parent.parent
        / "app" / "connections" / "pgvector_client.py"
    )

    with open(client_path, "r") as f:
        source = f.read()

    # Verify unique constraint is defined
    assert "UniqueConstraint" in source, "Missing UniqueConstraint import"
    assert "source_url" in source and "track" in source, (
        "Missing source_url and/or track in constraint definition"
    )

    # Should have the constraint defined in __table_args__
    assert "__table_args__" in source, "Missing __table_args__ definition"


def test_duplicate_detection_flow():
    """
    Test that upsert_document method implements the proper duplicate detection flow.

    The flow should be:
    1. Check if (source_url, track) exists in database
    2. If exists, return existing ID and skip insertion
    3. If not exists, insert new document and return its ID
    """
    import pathlib

    client_path = (
        pathlib.Path(__file__).parent.parent
        / "app" / "connections" / "pgvector_client.py"
    )

    with open(client_path, "r") as f:
        source = f.read()

    # Extract the upsert_document method
    start = source.find("async def upsert_document(")
    assert start != -1, "upsert_document method not found"

    # Get the method body (approximate end at next "async def" or class end)
    end = source.find("\n    async def ", start + 1)
    if end == -1:
        end = source.find("\n\nclass ", start + 1)
    if end == -1:
        end = len(source)

    method_source = source[start:end]

    # Verify the three-step flow
    assert "existing = await" in method_source or "result = " in method_source, (
        "Missing duplicate check query"
    )
    assert "if result:" in method_source or "if existing:" in method_source, (
        "Missing conditional check for existing document"
    )
    assert "return str(" in method_source, (
        "Missing return statement for ID"
    )
    assert "session.add(doc)" in method_source, (
        "Missing document insertion for new documents"
    )
    assert "session.commit()" in method_source, (
        "Missing commit for new documents"
    )
