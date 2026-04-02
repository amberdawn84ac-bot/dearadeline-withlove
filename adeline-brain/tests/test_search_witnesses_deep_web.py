"""
Test suite for search_witnesses() deep web search acquisition.

Tests that search_witnesses():
1. Returns Hippocampus results if any clear 0.82 threshold
2. Triggers deep web search when Hippocampus is empty
3. Embeds and persists newly acquired documents
4. Returns newly acquired docs as VERIFIED evidence
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tools.researcher import search_witnesses


@pytest.mark.asyncio
async def test_search_witnesses_returns_hippocampus_results():
    """search_witnesses() should return Hippocampus results if any clear 0.82 threshold."""
    mock_embedding = [0.1] * 1536

    with patch('app.tools.researcher.openai.AsyncOpenAI') as mock_openai_class, \
         patch('app.tools.researcher.hippocampus.similarity_search') as mock_search:

        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=mock_embedding)]
        mock_client.embeddings.create = AsyncMock(return_value=mock_embed_response)

        # Mock Hippocampus returning a verified source
        mock_search.return_value = [
            {
                'id': '123',
                'source_title': 'Presidential Records',
                'source_url': 'https://archives.gov/...',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'Executive order text...',
                'similarity_score': 0.89,
                'citation_author': 'Kennedy, J.',
                'citation_year': 1963,
                'citation_archive_name': 'NARA',
            }
        ]

        results = await search_witnesses(
            query="Cold War foreign policy decisions",
            track="TRUTH_HISTORY"
        )

        assert len(results) == 1
        assert results[0]['verdict'] == 'VERIFIED'
        assert results[0]['source_type'] == 'DECLASSIFIED_GOV'


@pytest.mark.asyncio
async def test_search_witnesses_triggers_deep_search_when_hippocampus_empty():
    """search_witnesses() should trigger deep web search if Hippocampus returns nothing."""
    mock_embedding = [0.1] * 1536

    with patch('app.tools.researcher.openai.AsyncOpenAI') as mock_openai_class, \
         patch('app.tools.researcher.hippocampus.similarity_search') as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel') as mock_deep_search:

        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=mock_embedding)]
        mock_client.embeddings.create = AsyncMock(return_value=mock_embed_response)

        mock_hippo.return_value = []  # Hippocampus has nothing

        mock_deep_search.return_value = [
            {
                'title': 'FBI Vault: COINTELPRO Files',
                'url': 'https://vault.fbi.gov/cointelpro-files/...',
                'archive': 'FBI_VAULT',
                'snippet': 'Declassified FBI surveillance program documentation...',
            }
        ]

        results = await search_witnesses(
            query="COINTELPRO surveillance program",
            track="JUSTICE_CHANGEMAKING"
        )

        # Deep search should be triggered
        mock_deep_search.assert_called_once()


@pytest.mark.asyncio
async def test_search_witnesses_persists_acquired_documents():
    """search_witnesses() should embed and persist newly acquired documents to Hippocampus."""
    mock_query_embedding = [0.1] * 1536
    mock_doc_embedding = [0.2] * 1536

    with patch('app.tools.researcher.openai.AsyncOpenAI') as mock_openai_class, \
         patch('app.tools.researcher.hippocampus.similarity_search') as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel') as mock_deep_search, \
         patch('app.tools.researcher.hippocampus.upsert_document') as mock_upsert:

        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # First call embeds the query, second call embeds the document
        embed_responses = [
            MagicMock(data=[MagicMock(embedding=mock_query_embedding)]),
            MagicMock(data=[MagicMock(embedding=mock_doc_embedding)]),
        ]
        mock_client.embeddings.create = AsyncMock(side_effect=embed_responses)

        mock_hippo.return_value = []

        mock_deep_search.return_value = [
            {
                'title': 'Congressional Record: Civil Rights Act Debate',
                'url': 'https://congress.gov/...',
                'archive': 'CONGRESSIONAL_RECORD',
                'snippet': 'Full text of debate on civil rights legislation...',
            }
        ]

        mock_upsert.return_value = 'doc-uuid-123'

        results = await search_witnesses(
            query="Civil Rights Act debate 1964",
            track="TRUTH_HISTORY"
        )

        # Should call upsert for each found document
        mock_upsert.assert_called()
        call_args = mock_upsert.call_args
        assert call_args.kwargs['source_type'] == 'DECLASSIFIED_GOV'
        assert call_args.kwargs['track'] == 'TRUTH_HISTORY'

        # Result should be returned
        assert len(results) == 1
        assert results[0]['source_title'] == 'Congressional Record: Civil Rights Act Debate'


@pytest.mark.asyncio
async def test_search_witnesses_filters_by_threshold():
    """search_witnesses() should filter results by 0.82 threshold."""
    # Create base embedding vector
    mock_query_embedding = [0.1] * 1536

    # Create a very different embedding for low score (perpendicular vector)
    mock_low_score_embedding = [1.0 if i % 2 == 0 else 0.0 for i in range(1536)]
    # Create a very similar embedding for high score
    mock_high_score_embedding = [0.1] * 1536

    with patch('app.tools.researcher.openai.AsyncOpenAI') as mock_openai_class, \
         patch('app.tools.researcher.hippocampus.similarity_search') as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel') as mock_deep_search, \
         patch('app.tools.researcher.hippocampus.upsert_document') as mock_upsert:

        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # First call embeds the query, then embeddings for each document
        embed_responses = [
            MagicMock(data=[MagicMock(embedding=mock_query_embedding)]),
            MagicMock(data=[MagicMock(embedding=mock_low_score_embedding)]),  # Low score (perpendicular)
            MagicMock(data=[MagicMock(embedding=mock_high_score_embedding)]),  # High score (identical)
        ]
        mock_client.embeddings.create = AsyncMock(side_effect=embed_responses)

        mock_hippo.return_value = []

        mock_deep_search.return_value = [
            {
                'title': 'Low Relevance Doc',
                'url': 'https://example.com/low',
                'archive': 'NARA',
                'snippet': 'Not very relevant content...',
            },
            {
                'title': 'High Relevance Doc',
                'url': 'https://example.com/high',
                'archive': 'NARA',
                'snippet': 'Very relevant content that matches the query exactly...',
            },
        ]

        mock_upsert.return_value = 'doc-uuid-456'

        results = await search_witnesses(
            query="Important topic",
            track="TRUTH_HISTORY"
        )

        # Only one should be persisted (the high-score one)
        # upsert should be called once
        assert mock_upsert.call_count == 1

        # Results should contain only the high-score document
        assert len(results) == 1
        assert results[0]['source_title'] == 'High Relevance Doc'


@pytest.mark.asyncio
async def test_search_witnesses_returns_empty_when_all_fail():
    """search_witnesses() should return empty list if both Hippocampus and deep search fail."""
    mock_embedding = [0.1] * 1536

    with patch('app.tools.researcher.openai.AsyncOpenAI') as mock_openai_class, \
         patch('app.tools.researcher.hippocampus.similarity_search') as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel') as mock_deep_search:

        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        mock_embed_response = MagicMock()
        mock_embed_response.data = [MagicMock(embedding=mock_embedding)]
        mock_client.embeddings.create = AsyncMock(return_value=mock_embed_response)

        mock_hippo.return_value = []
        mock_deep_search.return_value = []  # No results from deep search either

        results = await search_witnesses(
            query="Obscure topic",
            track="TRUTH_HISTORY"
        )

        assert results == []
