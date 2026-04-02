"""
Seed scripts for ingesting declassified government documents into Hippocampus.

Fetches documents from government archives (NARA, CIA FOIA, FBI Vault),
parses them using DeclassifiedDocument parser, embeds with text-embedding-3-small,
and persists to Hippocampus with source_type=DECLASSIFIED_GOV.

Usage:
    python -c "
    import asyncio
    from app.scripts.seed_declassified_documents import seed_all_declassified_documents
    asyncio.run(seed_all_declassified_documents())
    "
"""
import asyncio
import httpx
import logging
import os
from typing import Optional

from openai import AsyncOpenAI

from app.connections.pgvector_client import hippocampus
from app.tools.declassified_parser import parse_declassified_document
from app.tools.researcher import search_archive_async
from app.schemas.api_models import SourceType

logger = logging.getLogger(__name__)

# Lazy-initialize OpenAI client (defer until first use)
openai_client = None


def _get_openai_client():
    """Lazy-initialize OpenAI client on first use."""
    global openai_client
    if openai_client is None:
        openai_client = AsyncOpenAI()
    return openai_client


# ── Search queries tailored to each track ──────────────────────────────────

TRACK_QUERIES = {
    "TRUTH_HISTORY": [
        "American history declassified documents",
        "presidential records foreign policy",
        "government decision-making Cold War",
        "State Department memos diplomatic history",
    ],
    "JUSTICE_CHANGEMAKING": [
        "civil rights movement declassified documents",
        "government surveillance COINTELPRO",
        "regulatory capture legislative history",
        "FBI civil rights surveillance documents",
    ],
}


# ── Utility functions ──────────────────────────────────────────────────────

async def fetch_document_text(url: str) -> Optional[str]:
    """
    Fetch document text from archive URL.

    Args:
        url: URL to fetch from

    Returns:
        Document text if successful, None on failure
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"[Fetch] HTTP {response.status_code}: {url}")
    except Exception as e:
        logger.warning(f"[Fetch] Failed to fetch {url}: {e}")
    return None


# ── Seed functions for individual archives ──────────────────────────────────

async def seed_nara_documents(track: str, limit: int = 10) -> int:
    """
    Seed NARA (National Archives and Records Administration) documents into Hippocampus.

    Searches for documents relevant to the given track.

    Args:
        track: Track name (TRUTH_HISTORY, JUSTICE_CHANGEMAKING, etc.)
        limit: Max documents to ingest per query

    Returns:
        Number of chunks ingested
    """
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("[NARA] TAVILY_API_KEY not set — skipping NARA seed")
        return 0

    queries = TRACK_QUERIES.get(track, [f"{track} declassified documents"])
    ingested_count = 0

    for query in queries:
        try:
            logger.info(f"[NARA] Searching: {query}")

            results = await search_archive_async(query, "NARA")

            for result in results[:limit]:
                try:
                    url = result.get("url", "")
                    title = result.get("title", "Untitled NARA Document")
                    snippet = result.get("snippet", "")

                    if not snippet:
                        logger.warning(f"[NARA] No snippet for {title}")
                        continue

                    # Parse snippet into chunks
                    chunks = parse_declassified_document(
                        raw_text=snippet,
                        archive_name="NARA",
                        source_url=url,
                    )

                    if not chunks:
                        continue

                    # Embed and persist each chunk
                    for chunk in chunks:
                        try:
                            # Embed with text-embedding-3-small
                            client = _get_openai_client()
                            embedding_response = await client.embeddings.create(
                                model="text-embedding-3-small",
                                input=chunk.chunk_text,
                            )
                            embedding = embedding_response.data[0].embedding

                            # Upsert to Hippocampus
                            doc_id = await hippocampus.upsert_document(
                                source_title=title,
                                track=track,
                                chunk=chunk.chunk_text,
                                embedding=embedding,
                                source_url=url,
                                source_type=SourceType.DECLASSIFIED_GOV.value,
                                citation_author=chunk.metadata.get("author", ""),
                                citation_year=None,
                                citation_archive_name="NARA",
                            )
                            ingested_count += 1
                            logger.info(f"[NARA] Ingested: {title[:50]}...")

                        except Exception as e:
                            logger.warning(f"[NARA] Failed to embed/persist chunk: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"[NARA] Failed to process document {title}: {e}")
                    continue

        except Exception as e:
            logger.error(f"[NARA] Error searching: {e}")
            continue

    logger.info(f"[NARA] Seed complete: {ingested_count} chunks ingested")
    return ingested_count


async def seed_cia_foia_documents(track: str, limit: int = 10) -> int:
    """
    Seed CIA FOIA documents into Hippocampus.

    Searches for declassified CIA documents relevant to the given track.

    Args:
        track: Track name (TRUTH_HISTORY, JUSTICE_CHANGEMAKING, etc.)
        limit: Max documents to ingest per query

    Returns:
        Number of chunks ingested
    """
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("[CIA FOIA] TAVILY_API_KEY not set — skipping CIA FOIA seed")
        return 0

    queries = TRACK_QUERIES.get(track, [f"{track} CIA documents"])
    ingested_count = 0

    for query in queries:
        try:
            logger.info(f"[CIA FOIA] Searching: {query}")

            results = await search_archive_async(query, "CIA_FOIA")

            for result in results[:limit]:
                try:
                    url = result.get("url", "")
                    title = result.get("title", "Untitled CIA Document")
                    snippet = result.get("snippet", "")

                    if not snippet:
                        logger.warning(f"[CIA FOIA] No snippet for {title}")
                        continue

                    chunks = parse_declassified_document(
                        raw_text=snippet,
                        archive_name="CIA_FOIA",
                        source_url=url,
                    )

                    if not chunks:
                        continue

                    for chunk in chunks:
                        try:
                            client = _get_openai_client()
                            embedding_response = await client.embeddings.create(
                                model="text-embedding-3-small",
                                input=chunk.chunk_text,
                            )
                            embedding = embedding_response.data[0].embedding

                            doc_id = await hippocampus.upsert_document(
                                source_title=title,
                                track=track,
                                chunk=chunk.chunk_text,
                                embedding=embedding,
                                source_url=url,
                                source_type=SourceType.DECLASSIFIED_GOV.value,
                                citation_author=chunk.metadata.get("author", ""),
                                citation_year=None,
                                citation_archive_name="CIA_FOIA",
                            )
                            ingested_count += 1
                            logger.info(f"[CIA FOIA] Ingested: {title[:50]}...")

                        except Exception as e:
                            logger.warning(f"[CIA FOIA] Failed to embed/persist chunk: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"[CIA FOIA] Failed to process document {title}: {e}")
                    continue

        except Exception as e:
            logger.error(f"[CIA FOIA] Error searching: {e}")
            continue

    logger.info(f"[CIA FOIA] Seed complete: {ingested_count} chunks ingested")
    return ingested_count


async def seed_fbi_vault_documents(track: str, limit: int = 10) -> int:
    """
    Seed FBI Vault documents into Hippocampus.

    Primarily targets JUSTICE_CHANGEMAKING track (surveillance, civil rights, COINTELPRO).

    Args:
        track: Track name (typically JUSTICE_CHANGEMAKING, TRUTH_HISTORY)
        limit: Max documents to ingest per query

    Returns:
        Number of chunks ingested
    """
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("[FBI Vault] TAVILY_API_KEY not set — skipping FBI Vault seed")
        return 0

    queries = TRACK_QUERIES.get(track, [f"{track} FBI documents"])
    ingested_count = 0

    for query in queries:
        try:
            logger.info(f"[FBI Vault] Searching: {query}")

            results = await search_archive_async(query, "FBI_VAULT")

            for result in results[:limit]:
                try:
                    url = result.get("url", "")
                    title = result.get("title", "Untitled FBI Document")
                    snippet = result.get("snippet", "")

                    if not snippet:
                        logger.warning(f"[FBI Vault] No snippet for {title}")
                        continue

                    chunks = parse_declassified_document(
                        raw_text=snippet,
                        archive_name="FBI_VAULT",
                        source_url=url,
                    )

                    if not chunks:
                        continue

                    for chunk in chunks:
                        try:
                            client = _get_openai_client()
                            embedding_response = await client.embeddings.create(
                                model="text-embedding-3-small",
                                input=chunk.chunk_text,
                            )
                            embedding = embedding_response.data[0].embedding

                            doc_id = await hippocampus.upsert_document(
                                source_title=title,
                                track=track,
                                chunk=chunk.chunk_text,
                                embedding=embedding,
                                source_url=url,
                                source_type=SourceType.DECLASSIFIED_GOV.value,
                                citation_author=chunk.metadata.get("author", ""),
                                citation_year=None,
                                citation_archive_name="FBI_VAULT",
                            )
                            ingested_count += 1
                            logger.info(f"[FBI Vault] Ingested: {title[:50]}...")

                        except Exception as e:
                            logger.warning(f"[FBI Vault] Failed to embed/persist chunk: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"[FBI Vault] Failed to process document {title}: {e}")
                    continue

        except Exception as e:
            logger.error(f"[FBI Vault] Error searching: {e}")
            continue

    logger.info(f"[FBI Vault] Seed complete: {ingested_count} chunks ingested")
    return ingested_count


# ── Master seed function ──────────────────────────────────────────────────

async def seed_all_declassified_documents() -> int:
    """
    Seed documents from all 3 primary archives for all relevant tracks.

    Runs all seeds in parallel for efficiency.

    Returns:
        Total number of chunks ingested across all archives
    """
    logger.info("[Seed] Starting declassified documents ingestion...")

    # Connect to Hippocampus
    await hippocampus.connect()
    logger.info("[Seed] Connected to Hippocampus")

    tasks = [
        seed_nara_documents(track="TRUTH_HISTORY", limit=5),
        seed_cia_foia_documents(track="TRUTH_HISTORY", limit=5),
        seed_fbi_vault_documents(track="JUSTICE_CHANGEMAKING", limit=5),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_count = sum(r for r in results if isinstance(r, int))
    logger.info(f"[Seed] Complete: {total_count} total chunks ingested")
    return total_count
