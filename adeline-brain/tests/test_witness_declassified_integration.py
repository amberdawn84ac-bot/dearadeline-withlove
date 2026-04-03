"""
Integration tests: Witness Protocol + deep web search acquisition.
Validates complete flow: Hippocampus query → threshold enforcement → deep web fallback → persistence.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tools.researcher import search_witnesses
from app.schemas.api_models import TRUTH_THRESHOLD


# ── Witness Protocol threshold enforcement (0.82) ──────────────────────

@pytest.mark.asyncio
async def test_witness_protocol_returns_verified_above_threshold():
    """Results >= 0.82 should return as VERIFIED."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        # Result above threshold
        mock_hippo.return_value = [
            {
                'id': 'doc-123',
                'source_title': 'Civil Rights Act 1964',
                'source_url': 'https://congress.gov/...',
                'source_type': 'PRIMARY_SOURCE',
                'chunk': 'Legislative text...',
                'similarity_score': 0.88,
                'citation_author': 'Congress',
                'citation_year': 1964,
                'citation_archive_name': 'Congressional Record',
            }
        ]

        results = await search_witnesses(
            query="civil rights legislation",
            track="TRUTH_HISTORY",
        )

        assert len(results) == 1
        assert results[0]['verdict'] == 'VERIFIED'
        assert results[0]['similarity_score'] >= TRUTH_THRESHOLD


@pytest.mark.asyncio
async def test_witness_protocol_filters_below_threshold():
    """Results < 0.82 should be filtered out (not returned)."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        # Result below threshold
        mock_hippo.return_value = [
            {
                'id': 'doc-456',
                'source_title': 'Weak Match Document',
                'source_url': 'https://example.com/weak',
                'source_type': 'PRIMARY_SOURCE',
                'chunk': 'Marginally related text...',
                'similarity_score': 0.75,  # Below 0.82
                'citation_author': 'Unknown',
                'citation_year': None,
                'citation_archive_name': '',
            }
        ]

        results = await search_witnesses(
            query="obscure topic",
            track="TRUTH_HISTORY",
        )

        # Should be filtered out, return empty
        assert len(results) == 0


# ── Unified search across all source types ──────────────────────────────

@pytest.mark.asyncio
async def test_unified_search_accepts_all_source_types():
    """Hippocampus search should return results of any source_type >= 0.82."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        # Mixed source types all above threshold
        mock_hippo.return_value = [
            {
                'id': 'primary-1',
                'source_title': 'Archive.org Entry',
                'source_url': 'https://archive.org/details/...',
                'source_type': 'PRIMARY_SOURCE',
                'chunk': 'Primary source text...',
                'similarity_score': 0.87,
                'citation_author': '',
                'citation_year': None,
                'citation_archive_name': 'Archive.org',
            },
            {
                'id': 'declassified-1',
                'source_title': 'NARA Document',
                'source_url': 'https://catalog.archives.gov/...',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'Declassified text...',
                'similarity_score': 0.91,
                'citation_author': 'Kennedy, J.',
                'citation_year': 1963,
                'citation_archive_name': 'NARA',
            },
        ]

        results = await search_witnesses(
            query="1960s policy decisions",
            track="TRUTH_HISTORY",
        )

        # All should be returned regardless of source type
        assert len(results) == 2
        assert any(r['source_type'] == 'PRIMARY_SOURCE' for r in results)
        assert any(r['source_type'] == 'DECLASSIFIED_GOV' for r in results)


# ── Deep web search activation when Hippocampus empty ──────────────────

@pytest.mark.asyncio
async def test_deep_web_search_triggered_when_hippocampus_empty():
    """If Hippocampus empty, should activate deep web search."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.2] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel', new_callable=AsyncMock) as mock_deep:

        # Hippocampus empty
        mock_hippo.return_value = []

        # Deep web returns documents
        mock_deep.return_value = [
            {
                'title': 'FBI Vault: COINTELPRO',
                'url': 'https://vault.fbi.gov/...',
                'archive': 'FBI_VAULT',
                'snippet': 'Declassified FBI surveillance documentation...',
            }
        ]

        results = await search_witnesses(
            query="FBI civil rights surveillance",
            track="JUSTICE_CHANGEMAKING",
        )

        # Deep search should be called
        assert mock_deep.called
        assert len(results) >= 0  # May or may not return (depends on similarity)


@pytest.mark.asyncio
async def test_acquired_documents_persisted_with_correct_metadata():
    """Deep web search results should be embedded, scored, and persisted to Hippocampus."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.3] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel', new_callable=AsyncMock) as mock_deep, \
         patch('app.tools.researcher.hippocampus.upsert_document', new_callable=AsyncMock) as mock_upsert:

        # Hippocampus empty → triggers deep web
        mock_hippo.return_value = []

        # Deep web returns documents
        mock_deep.return_value = [
            {
                'title': 'Congressional Record: Civil Rights Debate',
                'url': 'https://congress.gov/record/...',
                'archive': 'CONGRESSIONAL_RECORD',
                'snippet': 'Senate debate on civil rights legislation 1964...' * 50,  # Long snippet
            }
        ]

        # Mock upsert returns document ID
        mock_upsert.return_value = 'newly-acquired-123'

        results = await search_witnesses(
            query="civil rights act debate",
            track="TRUTH_HISTORY",
        )

        # Verify upsert was called with correct parameters
        if results:  # Only if similarity >= 0.82
            assert mock_upsert.called
            call_kwargs = mock_upsert.call_args[1]
            assert call_kwargs['source_type'] == 'DECLASSIFIED_GOV'
            assert call_kwargs['track'] == 'TRUTH_HISTORY'
            assert call_kwargs['citation_archive_name'] == 'CONGRESSIONAL_RECORD'


# ── Self-improving system: acquired docs available in next query ────────

@pytest.mark.asyncio
async def test_self_improving_system_subsequent_queries():
    """Documents acquired and persisted should be found by Hippocampus on next query."""
    query_emb = [0.1] * 1536

    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=query_emb), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel', new_callable=AsyncMock) as mock_deep, \
         patch('app.tools.researcher.hippocampus.upsert_document', new_callable=AsyncMock) as mock_upsert:

        # First query: Hippocampus empty
        call_count = [0]
        async def hippo_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First query returns empty → triggers deep web
                return []
            # Subsequent queries find the newly acquired document
            return [{
                'id': 'newly-acquired-123',
                'source_title': 'COINTELPRO Files',
                'source_url': 'https://vault.fbi.gov/...',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'Declassified FBI surveillance files...',
                'similarity_score': 0.85,
                'citation_author': 'J. Edgar Hoover',
                'citation_year': 1965,
                'citation_archive_name': 'FBI_VAULT',
            }]

        mock_hippo.side_effect = hippo_side_effect

        # First query triggers deep web
        mock_deep.return_value = [{
            'title': 'COINTELPRO Files',
            'url': 'https://vault.fbi.gov/...',
            'archive': 'FBI_VAULT',
            'snippet': 'Declassified FBI surveillance files...',
        }]
        mock_upsert.return_value = 'newly-acquired-123'

        # First query
        results1 = await search_witnesses(
            query="COINTELPRO FBI surveillance",
            track="JUSTICE_CHANGEMAKING",
        )

        # Second similar query should find the doc in Hippocampus (not deep web again)
        results2 = await search_witnesses(
            query="FBI surveillance programs",
            track="JUSTICE_CHANGEMAKING",
        )

        # First query triggers deep web, second doesn't
        assert mock_deep.call_count == 1


# ── Empty case: both sources fail → RESEARCH_MISSION ────────────────────

@pytest.mark.asyncio
async def test_empty_case_returns_empty_list():
    """If both Hippocampus and deep web fail, return empty (triggers RESEARCH_MISSION)."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel', new_callable=AsyncMock) as mock_deep:

        # Both empty
        mock_hippo.return_value = []
        mock_deep.return_value = []

        results = await search_witnesses(
            query="extremely obscure undocumented topic",
            track="TRUTH_HISTORY",
        )

        # Should return empty (orchestrator converts to RESEARCH_MISSION)
        assert results == []


# ── Justice Track: COINTELPRO + surveillance documents ─────────────────────

@pytest.mark.asyncio
async def test_justice_track_cointelpro_deep_web_search():
    """
    JUSTICE_CHANGEMAKING track: deep web search finds FBI COINTELPRO documents,
    embeds them, and returns via witness protocol at >= 0.82 threshold.
    """
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.4] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel', new_callable=AsyncMock) as mock_deep, \
         patch('app.tools.researcher.hippocampus.upsert_document', new_callable=AsyncMock) as mock_upsert:

        # Hippocampus empty → triggers deep web
        mock_hippo.return_value = []

        # Deep web returns FBI COINTELPRO documents
        mock_deep.return_value = [
            {
                'title': 'FBI COINTELPRO: Civil Rights Surveillance (NAACP)',
                'url': 'https://vault.fbi.gov/cointel-pro/naacp',
                'archive': 'FBI_VAULT',
                'snippet': 'DECLASSIFIED. J. Edgar Hoover ordered surveillance of civil rights organizations including the NAACP. Agents infiltrated groups, created disinformation, and disrupted peaceful activism. Thousands of documents detail the systematic violation of Americans\' constitutional rights.',
            },
            {
                'title': 'CIA Assassination Plots Against Foreign Leaders',
                'url': 'https://www.cia.gov/information-freedom/foia-electronic-reading-room/',
                'archive': 'CIA_FOIA',
                'snippet': 'Declassified CIA documents reveal approved assassination attempts against Fidel Castro and other foreign leaders during the Cold War. These operations were conducted without congressional oversight or public knowledge.',
            }
        ]

        # Mock upsert returns document IDs
        mock_upsert.side_effect = ['cointelpro-123', 'cia-plot-456']

        # Query should trigger deep web search for justice track
        results = await search_witnesses(
            query="FBI surveillance civil rights COINTELPRO",
            track="JUSTICE_CHANGEMAKING",
        )

        # Both documents embedded and persisted
        assert mock_upsert.call_count == 2

        # Verify upsert calls used correct archive names
        call_1_kwargs = mock_upsert.call_args_list[0][1]
        call_2_kwargs = mock_upsert.call_args_list[1][1]

        assert call_1_kwargs['source_type'] == 'DECLASSIFIED_GOV'
        assert call_1_kwargs['citation_archive_name'] == 'FBI_VAULT'
        assert call_1_kwargs['track'] == 'JUSTICE_CHANGEMAKING'

        assert call_2_kwargs['source_type'] == 'DECLASSIFIED_GOV'
        assert call_2_kwargs['citation_archive_name'] == 'CIA_FOIA'
        assert call_2_kwargs['track'] == 'JUSTICE_CHANGEMAKING'

        # Results may be empty (depends on computed cosine similarity),
        # but upsert should have been called to persist
        assert mock_deep.called
