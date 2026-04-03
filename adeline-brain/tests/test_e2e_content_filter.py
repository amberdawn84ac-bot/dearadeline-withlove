"""E2E tests for search_witnesses with age-gated content filtering."""
import pytest
from unittest.mock import AsyncMock, patch
from app.tools.researcher import search_witnesses


@pytest.mark.asyncio
async def test_child_query_filters_sensitive():
    """10-year-old doesn't see COINTELPRO documents."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1]*1536) as mock_embed, \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        mock_hippo.return_value = [
            {
                'id': 'cointelpro-doc',
                'source_title': 'FBI COINTELPRO Operations',
                'source_type': 'DECLASSIFIED_GOV',
                'source_url': 'https://vault.fbi.gov/cointel',
                'chunk': 'FBI Director authorized COINTELPRO surveillance of civil rights groups...',
                'similarity_score': 0.88,
                'citation_author': 'FBI',
                'citation_year': 1970,
                'citation_archive_name': 'FBI_VAULT',
            },
            {
                'id': 'normal-doc',
                'source_title': 'Civil Rights Act of 1964',
                'source_type': 'PRIMARY_SOURCE',
                'source_url': 'https://congress.gov/civil-rights-act',
                'chunk': 'Legislative text of civil rights act protecting voting...',
                'similarity_score': 0.85,
                'citation_author': 'Congress',
                'citation_year': 1964,
                'citation_archive_name': 'CONGRESSIONAL_RECORD',
            }
        ]

        results = await search_witnesses(
            query="civil rights",
            track="TRUTH_HISTORY",
            student_age=10,
        )

        # COINTELPRO filtered out, normal doc included
        assert len(results) == 1
        assert results[0]['source_id'] == 'normal-doc'
        assert 'Civil Rights Act' in results[0]['source_title']


@pytest.mark.asyncio
async def test_teen_query_sees_justice_docs():
    """16-year-old sees COINTELPRO documents in Justice track."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1]*1536) as mock_embed, \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        mock_hippo.return_value = [
            {
                'id': 'cointelpro-doc',
                'source_title': 'FBI COINTELPRO Operations',
                'source_type': 'DECLASSIFIED_GOV',
                'source_url': 'https://vault.fbi.gov/cointel',
                'chunk': 'FBI Director authorized COINTELPRO surveillance...',
                'similarity_score': 0.88,
                'citation_author': 'FBI',
                'citation_year': 1970,
                'citation_archive_name': 'FBI_VAULT',
            }
        ]

        results = await search_witnesses(
            query="COINTELPRO",
            track="JUSTICE_CHANGEMAKING",
            student_age=16,
        )

        # Should see COINTELPRO at age 16
        assert len(results) == 1
        assert 'cointelpro' in results[0]['source_title'].lower()


@pytest.mark.asyncio
async def test_no_age_means_no_filtering():
    """If age=None, all documents returned (no filtering)."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1]*1536) as mock_embed, \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        mock_hippo.return_value = [
            {
                'id': 'assassination-doc',
                'source_title': 'CIA Assassination Plots',
                'source_type': 'DECLASSIFIED_GOV',
                'source_url': 'https://cia.gov/foia/assassination',
                'chunk': 'CIA operations included assassination attempts against foreign leaders...',
                'similarity_score': 0.87,
                'citation_author': 'CIA',
                'citation_year': 1975,
                'citation_archive_name': 'CIA_FOIA',
            }
        ]

        results = await search_witnesses(
            query="CIA operations",
            track="JUSTICE_CHANGEMAKING",
            student_age=None,  # No filtering
        )

        # All documents returned when age=None
        assert len(results) == 1
        assert 'assassination' in results[0]['source_title'].lower()


@pytest.mark.asyncio
async def test_multiple_docs_mixed_age_filtering():
    """Filter a mix of age-appropriate and sensitive documents for a 13-year-old."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1]*1536) as mock_embed, \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        mock_hippo.return_value = [
            {
                'id': 'surveillance-ok-13',
                'source_title': 'NSA Surveillance Programs',
                'source_type': 'DECLASSIFIED_GOV',
                'source_url': 'https://nsarchive.gwu.edu/nsa',
                'chunk': 'Warrantless surveillance without oversight...',
                'similarity_score': 0.86,
                'citation_author': 'NSA',
                'citation_year': 2013,
                'citation_archive_name': 'DNSA',
            },
            {
                'id': 'torture-blocked-13',
                'source_title': 'Torture Memoranda - CIA',
                'source_type': 'DECLASSIFIED_GOV',
                'source_url': 'https://cia.gov/foia/torture',
                'chunk': 'Authorization of enhanced interrogation techniques...',
                'similarity_score': 0.84,
                'citation_author': 'CIA',
                'citation_year': 2004,
                'citation_archive_name': 'CIA_FOIA',
            },
        ]

        results = await search_witnesses(
            query="government oversight",
            track="JUSTICE_CHANGEMAKING",
            student_age=13,
        )

        # 13-year-old can see surveillance (min age 13) but NOT torture (min age 15)
        assert len(results) == 1
        assert results[0]['source_id'] == 'surveillance-ok-13'


@pytest.mark.asyncio
async def test_empty_hippocampus_filters_deep_web():
    """When Hippocampus is empty, deep web results are also filtered by age."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1]*1536) as mock_embed, \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo, \
         patch('app.tools.researcher.search_all_archives_parallel', new_callable=AsyncMock) as mock_archives, \
         patch('app.tools.researcher.hippocampus.upsert_document', new_callable=AsyncMock, return_value='new-doc-id') as mock_upsert, \
         patch('app.tools.researcher._cosine_similarity', return_value=0.87):

        # Hippocampus returns nothing
        mock_hippo.return_value = []

        # Deep web finds sensitive doc
        mock_archives.return_value = [
            {
                'title': 'Assassination Plot Details',
                'url': 'https://cia.gov/foia/assassination',
                'archive': 'CIA_FOIA',
                'snippet': 'CIA assassination plots against foreign leaders detailed here...',
            }
        ]

        results = await search_witnesses(
            query="CIA assassination",
            track="JUSTICE_CHANGEMAKING",
            student_age=10,
        )

        # Young student filters out assassination doc from deep web
        assert len(results) == 0


@pytest.mark.asyncio
async def test_age_14_can_see_genocide():
    """14-year-old can see genocide documents (min age 14)."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1]*1536) as mock_embed, \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        mock_hippo.return_value = [
            {
                'id': 'genocide-doc',
                'source_title': 'Holocaust Documentation',
                'source_type': 'DECLASSIFIED_GOV',
                'source_url': 'https://nara.gov/holocaust',
                'chunk': 'Nazi genocide of six million Jews documented in detail...',
                'similarity_score': 0.89,
                'citation_author': 'NARA',
                'citation_year': 1945,
                'citation_archive_name': 'NARA',
            }
        ]

        results = await search_witnesses(
            query="genocide history",
            track="TRUTH_HISTORY",
            student_age=14,
        )

        # 14-year-old can see genocide content
        assert len(results) == 1
        assert 'genocide' in results[0]['chunk'].lower()


@pytest.mark.asyncio
async def test_age_13_blocked_from_genocide():
    """13-year-old cannot see genocide documents (min age 14)."""
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1]*1536) as mock_embed, \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        mock_hippo.return_value = [
            {
                'id': 'genocide-doc',
                'source_title': 'Holocaust Documentation',
                'source_type': 'DECLASSIFIED_GOV',
                'source_url': 'https://nara.gov/holocaust',
                'chunk': 'Nazi genocide of six million Jews documented in detail...',
                'similarity_score': 0.89,
                'citation_author': 'NARA',
                'citation_year': 1945,
                'citation_archive_name': 'NARA',
            }
        ]

        results = await search_witnesses(
            query="genocide history",
            track="TRUTH_HISTORY",
            student_age=13,
        )

        # 13-year-old filtered out
        assert len(results) == 0
