"""
SearchWitnesses Tool — Adeline's Auto-Search Capability

Two-layer search for primary evidence:

Layer 1 (Hippocampus): Semantic search in verified corpus
  - Query all source types (PRIMARY_SOURCE, DECLASSIFIED_GOV, etc)
  - Return any result >= 0.82 TRUTH_THRESHOLD

Layer 2 (Deep Web): Parallel search across 6 declassified archives
  - NARA, CIA FOIA, FBI Vault, Congressional Record, Federal Register, DNSA
  - Embed results and filter by 0.82 threshold
  - Persist newly acquired documents to Hippocampus (self-improving)

Flow:
  1. Embed query
  2. Unified Hippocampus search (all source types)
  3. If results >= 0.82: Return as VERIFIED
  4. If empty: Trigger parallel deep web search
  5. Embed found documents and filter by 0.82
  6. Persist acquired docs to Hippocampus
  7. Return newly acquired docs
  8. If both empty: Return [] (triggers RESEARCH_MISSION)
"""
import asyncio
import os
import logging
from typing import Optional

import httpx
import numpy as np
import openai

from app.schemas.api_models import (
    Evidence, EvidenceVerdict, WitnessCitation, TRUTH_THRESHOLD, SourceType,
)
from app.connections.pgvector_client import hippocampus

logger = logging.getLogger(__name__)

EMBED_MODEL       = "text-embedding-3-small"
TAVILY_URL        = "https://api.tavily.com/search"
TAVILY_TIMEOUT    = 15.0

DECLASSIFIED_DOMAINS = {
    'NARA': 'catalog.archives.gov',
    'CIA_FOIA': 'cia.gov/information-freedom',
    'FBI_VAULT': 'vault.fbi.gov',
    'CONGRESSIONAL_RECORD': 'congress.gov/congressional-record',
    'FEDERAL_REGISTER': 'federalregister.gov',
    'DNSA': 'nsarchive.gwu.edu',
}


# ── Cosine similarity helper ───────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


# ── OpenAI embedding helper ────────────────────────────────────────────────────

async def _embed(text: str) -> list[float]:
    """Embed text using text-embedding-3-small."""
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return resp.data[0].embedding


# ── Deep web search helpers ────────────────────────────────────────────────────

async def search_archive_async(query: str, archive_name: str) -> list[dict]:
    """
    Search a single declassified archive via Tavily.
    Returns list of documents with title, url, archive, snippet.
    """
    domain = DECLASSIFIED_DOMAINS.get(archive_name)
    if not domain:
        return []

    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        logger.warning(f"[Researcher] TAVILY_API_KEY not set — skipping {archive_name}")
        return []

    search_query = f'{query} site:{domain}'
    payload = {
        "api_key": api_key,
        "query": search_query,
        "include_domains": [domain],
        "max_results": 3,
        "search_depth": "basic",
    }

    try:
        async with httpx.AsyncClient(timeout=TAVILY_TIMEOUT) as client:
            resp = await client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()

            results = []
            for result in resp.json().get('results', []):
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'archive': archive_name,
                    'snippet': result.get('content', ''),
                })
            return results
    except Exception as e:
        logger.warning(f"[Researcher] Failed to search {archive_name}: {e}")
        return []


async def search_all_archives_parallel(query: str) -> list[dict]:
    """
    Search all 6 declassified archives in parallel.
    Returns deduplicated list of documents across all archives.
    """
    archives = list(DECLASSIFIED_DOMAINS.keys())
    tasks = [search_archive_async(query, archive) for archive in archives]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Deduplicate by URL
    seen_urls = set()
    deduplicated = []
    for result_list in all_results:
        if isinstance(result_list, list):
            for result in result_list:
                if result['url'] not in seen_urls:
                    seen_urls.add(result['url'])
                    deduplicated.append(result)

    return deduplicated


# ── Main search_witnesses() API ────────────────────────────────────────────────

async def search_witnesses(
    query: str,
    track: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Search for evidence to answer a student question.

    Flow:
    1. Embed query
    2. Search Hippocampus (all source types at >= 0.82)
    3. If found: Return results
    4. If empty: Deep web search across 6 declassified archives
    5. Embed + persist found docs to Hippocampus
    6. Return newly acquired docs
    7. If still empty: Return empty (triggers RESEARCH_MISSION)

    Returns list of Evidence dicts with verdict, source_type, etc.
    """
    try:
        logger.info(f"[Researcher] Searching for witnesses — query='{query}' track={track}")

        # Step 1: Embed the query
        embedding_response = await _embed(query)
        query_embedding = embedding_response

        # Step 2: Unified Hippocampus search (all source types)
        hippo_results = await hippocampus.similarity_search(
            query_embedding=query_embedding,
            track=track,
            top_k=top_k,
        )

        # Step 3: Filter by TRUTH_THRESHOLD (0.82)
        verified_results = [
            r for r in hippo_results
            if r.get('similarity_score', 0) >= TRUTH_THRESHOLD
        ]

        if verified_results:
            # Convert to Evidence format
            evidence_list = []
            for result in verified_results:
                evidence = {
                    'source_id': result['id'],
                    'source_title': result['source_title'],
                    'source_url': result['source_url'],
                    'source_type': result.get('source_type', 'PRIMARY_SOURCE'),
                    'witness_citation': {
                        'author': result.get('citation_author', ''),
                        'year': result.get('citation_year'),
                        'archive_name': result.get('citation_archive_name', ''),
                    },
                    'similarity_score': result['similarity_score'],
                    'verdict': 'VERIFIED',
                    'chunk': result['chunk'],
                }
                evidence_list.append(evidence)

            logger.info(f"[Researcher] Found {len(evidence_list)} verified in Hippocampus")
            return evidence_list

        # Step 4: Hippocampus empty → deep web search
        logger.info(f"[Researcher] Hippocampus empty. Triggering deep web search.")
        archive_results = await search_all_archives_parallel(query)

        if not archive_results:
            logger.info(f"[Researcher] No results from deep web search either.")
            return []

        # Step 5: Embed and score found documents
        acquired_evidence = []
        for doc in archive_results:
            try:
                # Embed the document snippet
                doc_embedding = await _embed(doc['snippet'][:8000])

                # Cosine similarity
                similarity_score = _cosine_similarity(query_embedding, doc_embedding)

                # Step 5b: Persist to Hippocampus if >= 0.82
                if similarity_score >= TRUTH_THRESHOLD:
                    doc_id = await hippocampus.upsert_document(
                        source_title=doc['title'],
                        track=track,
                        chunk=doc['snippet'],
                        embedding=doc_embedding,
                        source_url=doc['url'],
                        source_type=SourceType.DECLASSIFIED_GOV.value,
                        citation_author='',
                        citation_year=None,
                        citation_archive_name=doc['archive'],
                    )

                    acquired_evidence.append({
                        'source_id': doc_id,
                        'source_title': doc['title'],
                        'source_url': doc['url'],
                        'source_type': SourceType.DECLASSIFIED_GOV.value,
                        'witness_citation': {
                            'author': '',
                            'year': None,
                            'archive_name': doc['archive'],
                        },
                        'similarity_score': similarity_score,
                        'verdict': 'VERIFIED',
                        'chunk': doc['snippet'][:1000],
                    })

                    logger.info(f"[Researcher] Acquired document: {doc['title']} from {doc['archive']}")

            except Exception as e:
                logger.warning(f"[Researcher] Failed to process document {doc['title']}: {e}")
                continue

        if acquired_evidence:
            logger.info(f"[Researcher] Acquired {len(acquired_evidence)} documents from deep web search")
            return acquired_evidence

        # Step 7: Both empty → return empty
        logger.info(f"[Researcher] No results from any source. Student gets RESEARCH_MISSION.")
        return []

    except Exception as e:
        logger.error(f"[Researcher] Error in search_witnesses: {e}")
        return []
