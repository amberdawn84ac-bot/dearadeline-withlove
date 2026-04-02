"""
Tests for seed_declassified_documents module.

Tests verify that seed scripts for NARA, CIA FOIA, and FBI Vault:
1. Query archives via Tavily search
2. Fetch document text
3. Parse using DeclassifiedDocument parser
4. Embed chunks with text-embedding-3-small
5. Persist to Hippocampus with source_type=DECLASSIFIED_GOV
6. Log progress at each step
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.declassified_parser import ParsedChunk
from app.scripts.seed_declassified_documents import (
    seed_nara_documents,
    seed_cia_foia_documents,
    seed_fbi_vault_documents,
)


@pytest.mark.asyncio
async def test_seed_nara_documents_queries_and_ingests():
    """seed_nara_documents() should query NARA, fetch, parse, embed, and persist."""

    # Mock the parser to return a chunk
    mock_chunk = ParsedChunk(
        chunk_text="This is a sample chunk from a NARA document about Cold War strategy.",
        metadata={
            'archive_name': 'NARA',
            'source_url': 'https://catalog.archives.gov/id/12345',
            'title': 'Cold War Policy Memo',
            'date': '1963-01-15',
            'author': 'Secretary of State',
            'classification': 'DECLASSIFIED',
            'subject': 'Cold War Strategy',
        }
    )

    with patch('app.scripts.seed_declassified_documents.tavily_client') as mock_tavily, \
         patch('app.scripts.seed_declassified_documents.openai_client') as mock_openai, \
         patch('app.scripts.seed_declassified_documents.fetch_document_text') as mock_fetch, \
         patch('app.scripts.seed_declassified_documents.parse_declassified_document') as mock_parser, \
         patch('app.scripts.seed_declassified_documents.hippocampus') as mock_hippo:

        # Mock Tavily search to return document URLs
        # Note: seed_nara_documents will iterate through TRACK_QUERIES["TRUTH_HISTORY"]
        # We want one result per query
        mock_tavily.search.return_value = {
            'results': [
                {
                    'title': 'Cold War Policy Memo',
                    'url': 'https://catalog.archives.gov/id/12345',
                    'content': 'This document discusses Cold War policy...'
                }
            ]
        }

        # Mock HTTP fetch
        mock_fetch.return_value = """
            FROM: Secretary of State
            DATE: January 15, 1963
            SUBJECT: Cold War Strategy

            This is the full document text about Cold War policy decisions.
            The United States faced significant strategic challenges during this period.
        """

        # Mock parser
        mock_parser.return_value = [mock_chunk]

        # Mock embedding
        mock_embedding = [0.1] * 1536
        mock_openai.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=mock_embedding)])
        )

        # Mock Hippocampus upsert
        mock_hippo.upsert_document = AsyncMock(return_value="doc_id_123")

        # Run seed with limit=1 per query
        count = await seed_nara_documents(track="TRUTH_HISTORY", limit=1)

        # We expect 4 chunks total because there are 4 queries in TRACK_QUERIES["TRUTH_HISTORY"]
        # and each returns 1 document with 1 chunk
        assert count == 4
        mock_tavily.search.assert_called()
        assert mock_openai.embeddings.create.called
        # upsert_document should be called 4 times (1 per query * 1 chunk per query)
        assert mock_hippo.upsert_document.call_count == 4

        # Verify upsert called with correct parameters
        call_args = mock_hippo.upsert_document.call_args
        assert call_args.kwargs['source_type'] == 'DECLASSIFIED_GOV'
        assert call_args.kwargs['track'] == 'TRUTH_HISTORY'
        assert call_args.kwargs['citation_archive_name'] == 'NARA'


@pytest.mark.asyncio
async def test_seed_cia_foia_documents_handles_empty_results():
    """seed_cia_foia_documents() should handle archives with no results gracefully."""

    with patch('app.scripts.seed_declassified_documents.tavily_client') as mock_tavily, \
         patch('app.scripts.seed_declassified_documents.openai_client') as mock_openai, \
         patch('app.scripts.seed_declassified_documents.fetch_document_text') as mock_fetch, \
         patch('app.scripts.seed_declassified_documents.hippocampus') as mock_hippo:

        # Mock empty search results
        mock_tavily.search.return_value = {'results': []}

        count = await seed_cia_foia_documents(track="TRUTH_HISTORY", limit=1)

        assert count == 0
        mock_tavily.search.assert_called()


@pytest.mark.asyncio
async def test_seed_fbi_vault_documents_routes_to_justice_changemaking():
    """seed_fbi_vault_documents() should target JUSTICE_CHANGEMAKING track."""

    mock_chunk = ParsedChunk(
        chunk_text="This document discusses civil rights surveillance.",
        metadata={
            'archive_name': 'FBI_VAULT',
            'source_url': 'https://vault.fbi.gov/cointelpro',
            'title': 'COINTELPRO Memo',
            'date': '1970-01-01',
            'author': 'FBI Director',
            'classification': 'DECLASSIFIED',
            'subject': 'Counterintelligence Program',
        }
    )

    with patch('app.scripts.seed_declassified_documents.tavily_client') as mock_tavily, \
         patch('app.scripts.seed_declassified_documents.openai_client') as mock_openai, \
         patch('app.scripts.seed_declassified_documents.fetch_document_text') as mock_fetch, \
         patch('app.scripts.seed_declassified_documents.parse_declassified_document') as mock_parser, \
         patch('app.scripts.seed_declassified_documents.hippocampus') as mock_hippo:

        mock_tavily.search.return_value = {
            'results': [
                {
                    'title': 'COINTELPRO Memo',
                    'url': 'https://vault.fbi.gov/cointelpro',
                }
            ]
        }

        mock_fetch.return_value = "Mock FBI document content"
        mock_parser.return_value = [mock_chunk]
        mock_embedding = [0.1] * 1536
        mock_openai.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=mock_embedding)])
        )
        mock_hippo.upsert_document = AsyncMock(return_value="doc_id_456")

        count = await seed_fbi_vault_documents(track="JUSTICE_CHANGEMAKING", limit=1)

        # 4 queries in TRACK_QUERIES["JUSTICE_CHANGEMAKING"], each returning 1 doc with 1 chunk
        assert count == 4

        # Verify that the FBI archive name was used
        call_args = mock_hippo.upsert_document.call_args
        assert call_args.kwargs['citation_archive_name'] == 'FBI_VAULT'


@pytest.mark.asyncio
async def test_seed_continues_on_document_fetch_failure():
    """Seed should continue to next document if fetch fails."""

    mock_chunk = ParsedChunk(
        chunk_text="Working document.",
        metadata={
            'archive_name': 'NARA',
            'source_url': 'https://catalog.archives.gov/id/67890',
            'title': 'Working Document',
            'date': '1960-01-01',
            'author': 'Someone',
            'classification': 'DECLASSIFIED',
            'subject': 'A Subject',
        }
    )

    with patch('app.scripts.seed_declassified_documents.tavily_client') as mock_tavily, \
         patch('app.scripts.seed_declassified_documents.openai_client') as mock_openai, \
         patch('app.scripts.seed_declassified_documents.fetch_document_text') as mock_fetch, \
         patch('app.scripts.seed_declassified_documents.parse_declassified_document') as mock_parser, \
         patch('app.scripts.seed_declassified_documents.hippocampus') as mock_hippo:

        # Return 2 documents: first fetch fails, second succeeds
        mock_tavily.search.return_value = {
            'results': [
                {'title': 'Broken', 'url': 'https://catalog.archives.gov/id/11111'},
                {'title': 'Working Document', 'url': 'https://catalog.archives.gov/id/67890'},
            ]
        }

        # First fetch returns None (failure), second returns text
        mock_fetch.side_effect = [None, "Valid document text"]
        mock_parser.return_value = [mock_chunk]
        mock_embedding = [0.1] * 1536
        mock_openai.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=mock_embedding)])
        )
        mock_hippo.upsert_document = AsyncMock(return_value="doc_id_success")

        count = await seed_nara_documents(track="TRUTH_HISTORY", limit=2)

        # Should have ingested 1 document (skipped the broken one)
        assert count == 1
        mock_hippo.upsert_document.assert_called_once()


@pytest.mark.asyncio
async def test_seed_without_tavily_client_returns_zero():
    """If Tavily client is not available, seed should return 0 with warning."""

    with patch('app.scripts.seed_declassified_documents.tavily_client', None):
        count = await seed_nara_documents(track="TRUTH_HISTORY", limit=1)
        assert count == 0
