from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest
from app.tools import researcher


@pytest.mark.asyncio
async def test_exhausted_credits_open_circuit_without_repeated_api_calls(monkeypatch):
    monkeypatch.setattr(researcher, '_embedding_retry_at', 0)
    response = httpx.Response(429, request=httpx.Request('POST', 'https://provider.test'))
    client = MagicMock()
    client.embeddings.create = AsyncMock(side_effect=openai.RateLimitError(
        'No credits', response=response, body={'code': 'credit_balance_exhausted'}
    ))
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=client)
    manager.__aexit__ = AsyncMock(return_value=False)
    with patch('openai.AsyncOpenAI', return_value=manager):
        for _ in range(2):
            with pytest.raises(researcher.ResearchUnavailable):
                await researcher._embed('A research query')
    client.embeddings.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_live_research_never_bypasses_evidence_gate_during_outage(monkeypatch):
    monkeypatch.setattr(researcher, '_embed', AsyncMock(side_effect=researcher.ResearchUnavailable('Unavailable')))
    assert await researcher.search_witnesses('A question', 'TRUTH_HISTORY') == []
    with pytest.raises(researcher.ResearchUnavailable):
        await researcher.search_witnesses('A question', 'TRUTH_HISTORY', raise_on_unavailable=True)


@pytest.mark.asyncio
async def test_nightly_job_stops_and_reports_dependency_failure(monkeypatch):
    from app.jobs.seed_thin_tracks import seed_thin_tracks
    search = AsyncMock(side_effect=researcher.ResearchUnavailable('No credits'))
    monkeypatch.setattr(researcher, 'search_witnesses', search)
    with pytest.raises(researcher.ResearchUnavailable):
        await seed_thin_tracks()
    search.assert_awaited_once()
    assert search.await_args.kwargs['raise_on_unavailable'] is True
