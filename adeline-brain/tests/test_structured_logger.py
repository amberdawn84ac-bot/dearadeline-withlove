import pytest
import logging
from io import StringIO
from app.utils.structured_logger import get_structured_logger


def test_structured_logger_includes_context():
    """Structured logger adds context fields to all messages."""
    # Create a string buffer to capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter('%(message)s'))

    # Get logger with context
    logger = get_structured_logger(
        name="test_logger",
        student_id="student_123",
        track="TRUTH_HISTORY",
        archive_name="NARA",
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Log a message
    logger.info("Document found")

    # Verify context is included in output
    log_output = log_stream.getvalue()
    assert "student_123" in log_output
    assert "TRUTH_HISTORY" in log_output
    assert "NARA" in log_output
    assert "Document found" in log_output


def test_structured_logger_without_context():
    """Structured logger works without optional context fields."""
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter('%(message)s'))

    # Get logger without context
    logger = get_structured_logger(name="test_logger_no_context")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Log a message
    logger.info("Basic message")

    # Should still work
    log_output = log_stream.getvalue()
    assert "Basic message" in log_output


def test_structured_logger_with_similarity_score():
    """Structured logger includes similarity score when provided."""
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter('%(message)s'))

    logger = get_structured_logger(
        name="test_logger_similarity",
        archive_name="NARA",
        similarity_score=0.85,
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("Evidence verified")

    log_output = log_stream.getvalue()
    assert "NARA" in log_output
    assert "0.85" in log_output
    assert "Evidence verified" in log_output


def test_structured_logger_ignores_none_values():
    """Structured logger doesn't include None values in context."""
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter('%(message)s'))

    logger = get_structured_logger(
        name="test_logger_none",
        student_id="student_456",
        track=None,  # None should be excluded
        archive_name=None,  # None should be excluded
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("Test message")

    log_output = log_stream.getvalue()
    assert "student_456" in log_output
    assert "track" not in log_output  # None values excluded
    assert "archive_name" not in log_output  # None values excluded
    assert "Test message" in log_output
