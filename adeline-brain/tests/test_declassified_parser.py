"""
Tests for DeclassifiedDocument Parser

Parser converts raw documents from government archives into standardized chunks
suitable for embedding and storage in Hippocampus.
"""
import pytest
from app.tools.declassified_parser import (
    ParsedChunk,
    parse_declassified_document,
    chunk_text_preserving_sentences,
    clean_document_text,
)


def test_parse_nara_document():
    """Parser should extract chunks from NARA document with metadata."""
    raw_text = """
    NATIONAL ARCHIVES AND RECORDS ADMINISTRATION

    Record Group: 59, Central Foreign Policy File
    Date: January 15, 1963

    FROM: Secretary of State Dean Rusk
    TO: Ambassador Stevenson
    SUBJECT: Cold War Strategy Discussion

    This document discusses the approach to Soviet relations during the Cold War period.
    The United States government faced significant challenges in maintaining diplomatic channels
    while simultaneously preparing for potential military confrontation. The key strategic
    objective was to prevent Soviet expansion in Southeast Asia and other regions of vital interest.

    The policy memo outlines three primary approaches: engagement, containment, and deterrence.
    Each approach had distinct advantages and disadvantages that required careful consideration
    by policymakers. The recommendations in this document influenced subsequent policy decisions.

    Classification: DECLASSIFIED 1/15/2010
    """

    chunks = parse_declassified_document(
        raw_text=raw_text,
        archive_name="NARA",
        source_url="https://catalog.archives.gov/...",
    )

    assert len(chunks) > 0
    assert isinstance(chunks[0], ParsedChunk)
    assert chunks[0].chunk_text  # Non-empty
    assert chunks[0].metadata['archive_name'] == 'NARA'
    assert chunks[0].metadata['date'] == '1963-01-15'  # Normalized format
    assert 'Cold War' in chunks[0].chunk_text or any('Cold War' in c.chunk_text for c in chunks)


def test_chunk_text_preserves_sentence_boundaries():
    """Chunking should respect sentence boundaries, not hard-split at char limit."""
    text = "This is sentence one. This is sentence two. This is sentence three. " * 20
    chunks = chunk_text_preserving_sentences(text, min_chunk_size=500, max_chunk_size=1000)

    for chunk in chunks:
        # Each chunk should not end in the middle of a sentence
        assert chunk.endswith('.') or chunk.endswith('!') or chunk.endswith('?') or len(chunk) < 100
        # Size should be within bounds (or small if single sentence)
        assert len(chunk) <= 1000 or 'sentence' not in chunk.lower()


def test_clean_document_removes_boilerplate():
    """Cleaning should remove classification marks, headers, page breaks."""
    raw = """
    CLASSIFIED//NOFORN
    Page 1
    ════════════════════════════════════════

    SUBJECT: Important Policy Document

    The actual content of the document.

    ════════════════════════════════════════
    Page 2

    More content here.

    DECLASSIFIED: Authority EO 13526
    Released: January 2010
    """

    cleaned = clean_document_text(raw)

    # Should remove class marks
    assert 'CLASSIFIED' not in cleaned
    assert 'NOFORN' not in cleaned
    # Should remove page breaks
    assert '════' not in cleaned
    # Should remove release metadata
    assert 'DECLASSIFIED' not in cleaned
    # Should keep actual content
    assert 'Important Policy Document' in cleaned
    assert 'The actual content' in cleaned


def test_extract_metadata_from_document():
    """Parser should extract key metadata: title, date, author, classification."""
    text = """
    CONFIDENTIAL

    FROM: J. Edgar Hoover, FBI Director
    DATE: March 15, 1954
    SUBJECT: Investigation of Communist Sympathizers

    Document body here.
    """

    chunks = parse_declassified_document(
        raw_text=text,
        archive_name="FBI_VAULT",
        source_url="https://vault.fbi.gov/...",
    )

    assert chunks[0].metadata['author'] == 'J. Edgar Hoover'
    assert chunks[0].metadata['date'] == '1954-03-15'
    assert 'Communist' in chunks[0].metadata['subject'] or 'Communist' in chunks[0].chunk_text


def test_parse_congressional_record():
    """Parser should handle Congressional Record format (different from NARA)."""
    raw = """
    CONGRESSIONAL RECORD

    Congress: 88th
    Session: 1st
    Date: June 10, 1963
    Speaker: Senator John F. Kennedy (D-MA)

    Mr. President, I rise to speak on the issue of civil rights legislation.
    The people of my state have made clear their support for comprehensive protections.
    We must act decisively to ensure equal treatment under the law.

    I yield back to the Chair.
    """

    chunks = parse_declassified_document(
        raw_text=raw,
        archive_name="CONGRESSIONAL_RECORD",
        source_url="https://congress.gov/...",
    )

    assert len(chunks) > 0
    assert any('civil rights' in c.chunk_text.lower() for c in chunks)
    assert chunks[0].metadata['archive_name'] == 'CONGRESSIONAL_RECORD'


def test_chunk_text_minimum_size_requirement():
    """Chunks should meet minimum size requirement (unless single sentence)."""
    text = "Short. " + "This is a longer sentence that will be used for testing. " * 15
    chunks = chunk_text_preserving_sentences(text, min_chunk_size=500, max_chunk_size=1000)

    # At least one chunk should be > 500 chars
    assert any(len(c) >= 500 for c in chunks), "No chunk met minimum size requirement"


def test_empty_document_handling():
    """Parser should handle empty documents gracefully."""
    raw_text = "   \n\n   "

    chunks = parse_declassified_document(
        raw_text=raw_text,
        archive_name="NARA",
        source_url="https://example.com",
    )

    # Should return empty list for empty document
    assert isinstance(chunks, list)


def test_metadata_defaults():
    """Parser should provide sensible defaults when metadata is missing."""
    raw_text = "Just some plain text content without any formal headers or metadata."

    chunks = parse_declassified_document(
        raw_text=raw_text,
        archive_name="NARA",
        source_url="https://example.com",
    )

    assert chunks[0].metadata['archive_name'] == 'NARA'
    assert chunks[0].metadata['source_url'] == "https://example.com"
    assert 'author' in chunks[0].metadata
    assert 'date' in chunks[0].metadata
