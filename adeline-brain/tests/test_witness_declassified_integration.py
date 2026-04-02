"""
Integration tests: Witness Protocol evaluates evidence consistently,
and search_witnesses finds sources from approved archives.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.protocols.witness import evaluate_evidence, EvidenceVerdict
from app.tools.researcher import search_witnesses, ALLOWED_DOMAINS


# ── Witness Protocol accepts all sources equally ──────────────────────

def test_witness_protocol_verifies_high_similarity_source():
    """Any source at 0.88 must be VERIFIED — threshold is applied equally."""
    evidence = evaluate_evidence(
        source_id="nara-2723456",
        source_title="Civil Rights Act - 1964 Legislative Record",
        similarity_score=0.88,
        chunk="Full text of the Civil Rights Act...",
        source_url="https://catalog.archives.gov/id/2723456",
        citation_author="National Archives",
        citation_year=1964,
        citation_archive_name="NARA",
    )
    assert evidence.verdict == EvidenceVerdict.VERIFIED
    assert evidence.similarity_score == 0.88


def test_witness_protocol_rejects_low_similarity_source():
    """Any source at 0.65 must be ARCHIVE_SILENT — same rules for all."""
    evidence = evaluate_evidence(
        source_id="archive-12345",
        source_title="Historical Document",
        similarity_score=0.65,
        chunk="Some content...",
        source_url="https://archive.org/details/12345",
        citation_author="Internet Archive",
        citation_year=1972,
        citation_archive_name="Archive.org",
    )
    assert evidence.verdict == EvidenceVerdict.ARCHIVE_SILENT


# ── Allowed domains for search ────────────────────────────────────────

def test_allowed_domains_includes_archives():
    """Search must include approved archive domains."""
    assert "archive.org" in ALLOWED_DOMAINS
    assert "gutenberg.org" in ALLOWED_DOMAINS
    assert "archives.gov" in ALLOWED_DOMAINS


# ── search_witnesses integration ──────────────────────────────────────

@pytest.mark.asyncio
@patch("app.tools.researcher._embed")
@patch("app.tools.researcher._tavily_search")
@patch("app.tools.researcher.neo4j_client")
async def test_search_witnesses_finds_and_verifies_source(
    mock_neo4j, mock_tavily, mock_embed
):
    """
    When search finds a document clearing the threshold,
    it must return a WitnessResult with VERIFIED verdict.
    """
    mock_tavily.return_value = [
        {
            "url": "https://catalog.archives.gov/id/299868",
            "title": "Civil Rights Act of 1964",
            "content": "An act to enforce the constitutional right to vote...",
        }
    ]
    query_emb = [0.9] * 1536
    mock_embed.return_value = query_emb  # Same vector = similarity 1.0
    mock_neo4j.run = AsyncMock()

    result = await search_witnesses(
        topic="civil rights act 1964",
        track="TRUTH_HISTORY",
        query_embedding=query_emb,
        lesson_id="lesson-123",
    )

    assert result is not None
    assert result.evidence.verdict == EvidenceVerdict.VERIFIED
    assert result.evidence.source_title == "Civil Rights Act of 1964"
    assert "archives.gov" in result.source_url


@pytest.mark.asyncio
@patch("app.tools.researcher._embed")
@patch("app.tools.researcher._tavily_search")
async def test_search_witnesses_returns_none_when_no_match(mock_tavily, mock_embed):
    """
    When no source clears the threshold, search_witnesses returns None.
    """
    mock_tavily.return_value = [
        {
            "url": "https://archive.org/details/weak",
            "title": "Weak Match",
            "content": "Unrelated content...",
        }
    ]
    # Return very different embedding = low similarity
    mock_embed.return_value = [0.1] * 1536

    result = await search_witnesses(
        topic="obscure topic",
        track="TRUTH_HISTORY",
        query_embedding=[0.9] * 1536,
        lesson_id="lesson-789",
    )

    assert result is None


@pytest.mark.asyncio
@patch("app.tools.researcher._tavily_search")
async def test_search_witnesses_returns_none_when_no_results(mock_tavily):
    """
    When Tavily returns no results, search_witnesses returns None.
    """
    mock_tavily.return_value = []

    result = await search_witnesses(
        topic="nonexistent topic",
        track="TRUTH_HISTORY",
        query_embedding=[0.9] * 1536,
        lesson_id="lesson-999",
    )

    assert result is None
