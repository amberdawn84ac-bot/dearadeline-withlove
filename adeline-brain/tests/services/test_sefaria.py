"""
Tests for Sefaria API integration service.
"""
import pytest
from app.services.sefaria import (
    detect_biblical_reference,
    normalize_reference,
    extract_text,
    fetch_biblical_text,
)


def test_detect_biblical_reference():
    """Test biblical reference detection in topics."""
    # English book names
    assert detect_biblical_reference("Tell me about Genesis 1:1") == "Genesis.1.1"
    assert detect_biblical_reference("Isaiah 43:1 - Fear not") == "Isaiah.43.1"
    assert detect_biblical_reference("Exodus 20") == "Exodus.20"
    
    # Hebrew book names
    assert detect_biblical_reference("Yeshayahu 43:1") == "Isaiah.43.1"
    assert detect_biblical_reference("Bereshit 1") == "Genesis.1"
    
    # No reference
    assert detect_biblical_reference("Tell me about farming") is None
    assert detect_biblical_reference("What is justice?") is None


def test_normalize_reference():
    """Test reference normalization."""
    assert normalize_reference("Genesis 1:1") == "Genesis.1.1"
    assert normalize_reference("Isaiah 43:1") == "Isaiah.43.1"
    assert normalize_reference("Yeshayahu 43:1") == "Isaiah.43.1"
    assert normalize_reference("Bereshit 1") == "Genesis.1"
    assert normalize_reference("Psalms 23:1-6") == "Psalms.23.1-6"


def test_extract_text():
    """Test text extraction from Sefaria responses."""
    # String response
    assert extract_text("Hello world") == "Hello world"
    
    # Array response
    assert extract_text(["First verse", "Second verse"]) == "First verse"
    
    # Empty responses
    assert extract_text([]) == ""
    assert extract_text("") == ""
    assert extract_text(None) == ""


@pytest.mark.asyncio
async def test_fetch_biblical_text_genesis():
    """Test fetching Genesis 1:1 from Sefaria API."""
    result = await fetch_biblical_text("Genesis.1.1")
    
    assert result is not None
    assert result["ref"] == "Genesis 1:1"
    assert "hebrew" in result
    assert "english" in result
    assert len(result["english"]) > 0
    assert result["url"] == "https://www.sefaria.org/Genesis.1.1"


@pytest.mark.asyncio
async def test_fetch_biblical_text_isaiah():
    """Test fetching Isaiah 43:1 from Sefaria API."""
    result = await fetch_biblical_text("Isaiah.43.1")
    
    assert result is not None
    assert "Isaiah 43:1" in result["ref"]
    assert "hebrew" in result
    assert "english" in result
    assert len(result["english"]) > 0
    assert "Isaiah" in result["url"]


@pytest.mark.asyncio
async def test_fetch_biblical_text_invalid():
    """Test fetching invalid reference returns empty or None."""
    result = await fetch_biblical_text("InvalidBook.1.1")
    
    # Should return None or empty result
    assert result is None or result.get("english") == ""
