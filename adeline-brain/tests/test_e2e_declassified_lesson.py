"""
End-to-end test: Lesson generation with declassified documents.
Verifies: Witness Protocol + Hippocampus search + DECLASSIFIED_GOV sources.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.tools.researcher import search_witnesses
from app.schemas.api_models import TRUTH_THRESHOLD, EvidenceVerdict


@pytest.mark.asyncio
async def test_e2e_history_lesson_with_nara_sources():
    """
    Full flow: Query → Hippocampus returns DECLASSIFIED_GOV → Witness filters at 0.82.

    Simulates: Student asks about a historical topic,
    Hippocampus has seeded NARA documents, Witness Protocol verifies them,
    Lesson receives VERIFIED primary sources.
    """
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        # Simulate Hippocampus already seeded with NARA documents
        mock_hippo.return_value = [
            {
                'id': 'nara-doc-001',
                'source_title': 'Declaration of Independence',
                'source_url': 'https://catalog.archives.gov/id/300003/image',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'We hold these truths to be self-evident, that all men are created equal...',
                'similarity_score': 0.89,  # Above 0.82 threshold
                'citation_author': 'Jefferson, T.',
                'citation_year': 1776,
                'citation_archive_name': 'NARA',
            },
            {
                'id': 'nara-doc-002',
                'source_title': 'Gettysburg Address',
                'source_url': 'https://catalog.archives.gov/id/299845/image',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'Four score and seven years ago our fathers brought forth on this continent...',
                'similarity_score': 0.86,  # Above threshold
                'citation_author': 'Lincoln, A.',
                'citation_year': 1863,
                'citation_archive_name': 'NARA',
            },
        ]

        # Query returns VERIFIED sources
        results = await search_witnesses(
            query="founding fathers and American independence",
            track="TRUTH_HISTORY",
        )

        # Both sources should be VERIFIED
        assert len(results) == 2
        assert all(r['verdict'] == EvidenceVerdict.VERIFIED.value for r in results)
        assert all(r['source_type'] == 'DECLASSIFIED_GOV' for r in results)
        assert all(r['similarity_score'] >= TRUTH_THRESHOLD for r in results)

        # Source titles preserved
        assert results[0]['source_title'] == 'Declaration of Independence'
        assert results[1]['source_title'] == 'Gettysburg Address'


@pytest.mark.asyncio
async def test_e2e_justice_lesson_with_fbi_vault_sources():
    """
    Full flow: Justice track lesson → FBI Vault + CIA documents → Witness Protocol.

    Simulates: Student asks about civil rights violations,
    Hippocampus returns FBI COINTELPRO + CIA surveillance documents,
    Witness Protocol verifies both as PRIMARY sources.
    """
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.2] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        # Simulate Hippocampus seeded with FBI + CIA documents
        mock_hippo.return_value = [
            {
                'id': 'fbi-vault-cointelpro-001',
                'source_title': 'FBI COINTELPRO Operations Against Civil Rights Groups',
                'source_url': 'https://vault.fbi.gov/cointel-pro/civil-rights',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'FBI Director J. Edgar Hoover authorized COINTELPRO to disrupt, neutralize, and discredit civil rights organizations...',
                'similarity_score': 0.88,  # Above threshold
                'citation_author': 'Hoover, J. Edgar',
                'citation_year': 1965,
                'citation_archive_name': 'FBI_VAULT',
            },
            {
                'id': 'cia-docs-foreign-intervention',
                'source_title': 'CIA Activities Against Foreign Governments',
                'source_url': 'https://www.cia.gov/information-freedom/records-available-online/',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'CIA operations included support for coup attempts and assassination plots without congressional oversight...',
                'similarity_score': 0.85,  # Above threshold
                'citation_author': '',
                'citation_year': 1970,
                'citation_archive_name': 'CIA_FOIA',
            },
        ]

        # Query justice track
        results = await search_witnesses(
            query="government surveillance and civil rights violations",
            track="JUSTICE_CHANGEMAKING",
        )

        # Both verified
        assert len(results) == 2
        assert all(r['verdict'] == EvidenceVerdict.VERIFIED.value for r in results)
        assert results[0]['source_type'] == 'DECLASSIFIED_GOV'
        assert results[1]['source_type'] == 'DECLASSIFIED_GOV'

        # Lesson can now use these DECLASSIFIED_GOV sources with full confidence
        print("✓ Justice track sources verified and ready for lesson")


@pytest.mark.asyncio
async def test_e2e_mixed_source_types():
    """
    Hippocampus returns mixed source types (PRIMARY_SOURCE + DECLASSIFIED_GOV).
    Witness Protocol accepts both equally, filters by similarity only.
    """
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.3] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo:

        mock_hippo.return_value = [
            {
                'id': 'archive-org-123',
                'source_title': 'Civil War Photographs (Archive.org)',
                'source_url': 'https://archive.org/details/civil-war-photos',
                'source_type': 'ARCHIVE_ORG',
                'chunk': 'Mathew Brady photographs showing battlefields and soldier camps...',
                'similarity_score': 0.84,
                'citation_author': 'Brady, M.',
                'citation_year': 1863,
                'citation_archive_name': 'Archive.org',
            },
            {
                'id': 'nara-congress-123',
                'source_title': 'Congressional Globe: Civil War Debates',
                'source_url': 'https://catalog.archives.gov/id/301789',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'Senator discussion of Reconstruction policy and civil rights amendments...',
                'similarity_score': 0.83,
                'citation_author': 'Congress',
                'citation_year': 1868,
                'citation_archive_name': 'CONGRESSIONAL_RECORD',
            },
        ]

        results = await search_witnesses(
            query="civil war and reconstruction",
            track="TRUTH_HISTORY",
        )

        # Both returned (unified search, not tiered)
        assert len(results) == 2
        assert {r['source_type'] for r in results} == {'ARCHIVE_ORG', 'DECLASSIFIED_GOV'}
        assert all(r['verdict'] == EvidenceVerdict.VERIFIED.value for r in results)
        print("✓ Unified search accepts all source types equally")
